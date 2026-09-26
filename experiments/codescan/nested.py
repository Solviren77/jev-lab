"""Experiment 10: nested Jev calls to cut false flags.

Candidates: run-11 answers at or above (per-question cutoff - 0.15).
Pattern 1 (localise, then judge):
  A. Pick one over the function's numbered lines: which line shows the problem? (+ none)
  B. Yes/No on that line with ±8 lines of context and the path facts: is the problem really here?
Pattern 5 (Jev picks, code fetches, Jev judges) for "absence" questions:
  A. Pick one over related functions (callees for size/validation, callers for errors/guards):
     which one most likely provides the protection? (+ none)
  B. Code fetches that function's source; Yes/No: does this code provide the protection?
Keep a flag only if 1A names a line, 1B >= 0.5, and (absence questions) 5B < 0.7.

  python3 nested.py --out run-12
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan
import security_ai as S
import taint

HERE = Path(__file__).parent
DESC = {
    "injection_string_build": "a SQL query, shell command, file path or HTML string is built by inserting a value "
                              "that could come from outside input, without parameters or escaping",
    "path_from_input": "a file is opened, read, written or served using a name or path that came from outside input "
                       "without a containment or allowlist check",
    "state_change_unguarded": "data is changed in response to a request with no origin, host or permission check",
    "ai_output_unvalidated": "an AI model's answer is used (read, shown, saved or acted on) without checking its "
                             "structure or allowed values",
    "ai_model_inline": "an AI model name, temperature or token limit is written as a literal",
    "ai_failure_unhandled": "an AI model call can fail (error, timeout, bad answer) with nothing catching or "
                            "reporting that failure",
    "ai_no_size_limit": "content (emails, documents, histories) is sent to an AI model with no limit on its size",
}
ANCHOR = {  # absence problems: point at the line where the missing protection would matter
    "ai_no_size_limit": "Which line sends or passes content (emails, documents, context, messages) toward an AI model?",
    "ai_failure_unhandled": "Which line calls an AI model or a function that calls one?",
    "ai_output_unvalidated": "Which line reads or uses an AI model's answer?",
    "state_change_unguarded": "Which line changes stored data (writes, updates, deletes, saves)?",
}
PROTECT = {  # question -> (where to look, protection question)
    "ai_no_size_limit": ("callees", "Does function {name} limit or reject the size of the content it is given "
                                    "before sending it to an AI model?"),
    "ai_output_unvalidated": ("callees", "Does function {name} check an AI model's answer against a schema or "
                                         "allowed values and reject bad answers before returning it?"),
    "ai_failure_unhandled": ("callers", "Does function {name} catch or report errors raised by its call to {target}?"),
    "state_change_unguarded": ("callers", "Does function {name} check the request's host, origin or permission "
                                          "before calling {target}?"),
}


def numbered(code):
    return {"L%d" % (i + 1): ln for i, ln in enumerate(code.splitlines()) if ln.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="run-12")
    a = ap.parse_args()
    out = HERE / a.out
    out.mkdir(exist_ok=True)
    G = json.loads((HERE / "run-11/GRAPH.json").read_text())["functions"]
    cut = json.loads((HERE / "run-11/CUTOFFS.json").read_text())
    res = json.loads((HERE / "run-11/RESULTS.json").read_text())
    code_of, cache = {}, {}
    def fn(key):
        if key not in code_of:
            rel = key.split("::")[0]
            if rel not in cache:
                cache[rel] = {"%s::%s:%d" % (rel, f["name"], f["line"]): f for f in scan.functions(S.REPO / rel)}
            code_of[key] = cache[rel].get(key)
        return code_of[key]
    by_name = {}
    for k, f in G.items():
        by_name.setdefault(f["name"], []).append(k)
    cands = [(r["key"], q, v) for r in res for q, v in r["jev"].items()
             if q in DESC and v >= cut[q] - 0.15]
    print("%d candidates" % len(cands))

    # round A of both patterns, all in parallel
    jobs = []
    for key, q, v in cands:
        f = fn(key)
        lines = numbered(f["code"])
        if len(lines) > 250:
            lines = dict(list(lines.items())[:250])
        crit = dict(lines, none="No line in this function shows the problem")
        jobs.append({"kind": "1A", "key": key, "q": q, "ids": [f["id"]], "mode": "function",
                     "state": {"file": key.split("::")[0], "function_name": f["name"],
                               "path_facts": taint.facts_for(G[key])},
                     "questions": {"line": {"type": "choice", "criteria": crit,
                                            "instructions": (ANCHOR[q].replace("Which line", "Which line of function "
                                                             + f["name"]) + " Choose none if no line does.")
                                            if q in ANCHOR else
                                            "Which line of function %s shows this problem: %s? "
                                            "Choose none if no line does." % (f["name"], DESC[q])}}})
        if q in PROTECT:
            where = PROTECT[q][0]
            rel = G[key]["callers"] if where == "callers" else list(G[key].get("model_calls_via", {}) or {}) \
                or [c for c in G[key]["callees"] if c in by_name][:40]
            opts = {n: "function %s" % n for n in rel if n in by_name}
            if opts:
                opts["none"] = "None of these"
                jobs.append({"kind": "5A", "key": key, "q": q, "ids": [f["id"]], "mode": "function",
                             "state": {"function_name": f["name"], "code": f["code"]},
                             "questions": {"who": {"type": "choice", "criteria": opts,
                                                   "instructions": "Which of these %s of %s is most likely to "
                                                                   "prevent this problem: %s?" % (where, f["name"], DESC[q])}}})
    t = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        ra = list(pool.map(scan.call, jobs))

    # round B, built from round A answers
    jobs2 = []
    picked = {}
    for r in ra:
        if "answers" not in r:
            continue
        key, q = r["key"], r["q"]
        f = fn(key)
        if r["kind"] == "1A":
            line = r["answers"]["line"]["choice"]
            picked[(key, q, "line")] = (line, r["answers"]["line"]["confidence"])
            if line == "none":
                continue
            i = int(line[1:]) - 1
            src = f["code"].splitlines()
            window = "\n".join("%s%s" % (">> " if j == i else "   ", src[j]) for j in range(max(0, i - 8), min(len(src), i + 9)))
            jobs2.append({"kind": "1B", "key": key, "q": q, "ids": [f["id"]], "mode": "function",
                          "state": {"function_name": f["name"], "code_around_marked_line": window,
                                    "path_facts": taint.facts_for(G[key])},
                          "questions": {"confirm": {"type": "noul", "instructions":
                                        "Does the line marked >> show this problem, with nothing shown here or in "
                                        "the path facts preventing it: %s?" % DESC[q]}}})
        else:
            who = r["answers"]["who"]["choice"]
            picked[(key, q, "who")] = (who, r["answers"]["who"]["confidence"])
            if who == "none":
                continue
            tgt = next((fn(k) for k in by_name.get(who, []) if fn(k)), None)
            if not tgt:
                continue
            jobs2.append({"kind": "5B", "key": key, "q": q, "ids": [tgt["id"]], "mode": "function",
                          "state": {"function_name": who, "code": tgt["code"]},
                          "questions": {"protects": {"type": "noul", "instructions":
                                        PROTECT[q][1].format(name=who, target=f["name"])}}})
    with ThreadPoolExecutor(16) as pool:
        rb = list(pool.map(scan.call, jobs2))
    cost = sum((x.get("meta") or {}).get("cost") or 0 for x in ra + rb)
    print("round A %d calls, round B %d calls, %.1fs, $%.4f, errors %d" % (
        len(ra), len(rb), time.monotonic() - t, cost, sum("error" in x for x in ra + rb)))

    b = {(x["key"], x["q"], x["kind"]): x["answers"] for x in rb if "answers" in x}
    rows = []
    for key, q, v in cands:
        line = picked.get((key, q, "line"), ("?", None))
        conf = b.get((key, q, "1B"), {}).get("confirm", {}).get("value")
        who = picked.get((key, q, "who"))
        prot = b.get((key, q, "5B"), {}).get("protects", {}).get("value")
        keep = line[0] not in ("none", "?") and (conf or 0) >= .5 and not (prot is not None and prot >= .7)
        rows.append({"key": key, "question": q, "first_pass": v, "flag_first_pass": v >= cut[q],
                     "line": line[0], "line_text": (numbered(fn(key)["code"]).get(line[0], "") if line[0].startswith("L") else ""),
                     "confirm": conf, "protector": who[0] if who else None, "protects": prot, "keep": keep})
    (out / "NESTED.json").write_text(json.dumps(rows, indent=1))

    truth = {(k, q): v for k, q, v in json.loads((HERE / "run-11/TRUTH.json").read_text())}
    for k, q, v in json.loads((HERE / "run-11/EXTRA_TRUTH.json").read_text()):
        truth[(k, q)] = v
    real = sum(truth.values())
    def summary(sel, label):
        tp = sum(truth.get((r["key"], r["question"]), False) for r in sel)
        unk = sum((r["key"], r["question"]) not in truth for r in sel)
        print("%-34s flags %3d  real %2d/%d  unreviewed %d" % (label, len(sel), tp, real, unk))
    summary([r for r in rows if r["flag_first_pass"]], "run-11 per-question cutoffs")
    summary([r for r in rows if r["flag_first_pass"] and r["keep"]], "  + nested filter")
    summary([r for r in rows if r["keep"]], "nested filter on wider candidates")
    lost = [r for r in rows if r["flag_first_pass"] and not r["keep"] and truth.get((r["key"], r["question"]))]
    for r in lost:
        print("   lost real:", r["key"], r["question"], "line", r["line"], "confirm", r["confirm"],
              "protector", r["protector"], r["protects"])


if __name__ == "__main__":
    main()
