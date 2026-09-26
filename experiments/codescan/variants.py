"""Experiment 2: five prompt variants on the experiment-1 files, all sent concurrently, scored
against the same blind reference (run-01/REFERENCE.json).

  python3 variants.py --out run-02 [--run]
"""
import argparse
import ast
import copy
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan

FILES = ["assistant.py", "provider.py", "matter_write.py", "triage.py", "workspace_actions.py"]
ROOT = Path.home() / "GitHub/Solviren77/docket-49/prototype"
KEYS = ["more_than_name", "mixes_io_logic", "repeated_work"]

V = {}
# control: experiment-1 prompt, rerun to measure run-to-run movement
V["control"] = {"q": scan.QUESTIONS, "c": scan.CRITERIA, "dup": scan.DUPLICATE}

# 1. statements instead of questions (TypeSafe: a statement works as well as a question)
V["statement"] = {"q": {
    "more_than_name": "Function {id} does more than its name and docstring say it does.",
    "mixes_io_logic": "Function {id} both reads or writes external data (files, network, database, environment, "
                      "subprocess) and also makes decisions about or transforms that data.",
    "repeated_work": "Function {id} redoes, on every call, work whose result is the same each time.",
}, "c": scan.CRITERIA, "dup": "Function {id} does substantially the same job as another function in this file."}

# 2. instructions only, no criteria (TypeSafe: try with and without criteria)
V["no_criteria"] = {"q": scan.QUESTIONS, "c": {}, "dup": scan.DUPLICATE}

# 3. boundary examples in the criteria (TypeSafe: put boundary cases in the criteria)
V["examples"] = {"q": scan.QUESTIONS, "c": {
    "more_than_name": {"true": "Yes if a reader would be surprised: e.g. a function named `post` that also fetches "
                               "credentials, a `check` that also writes records, one function that dispatches many "
                               "unrelated operations, or a long function doing validation, I/O, calls and formatting.",
                       "false": "No if every step serves the job the name states, even if the function is long."},
    "mixes_io_logic": {"true": "Yes: queries a database then filters or builds output from the rows; reads a file "
                               "then parses and decides; calls an API then branches on the response.",
                       "false": "No: only performs the I/O and returns it; or only computes on arguments it was given. "
                                "Calling a helper that does I/O counts as I/O."},
    "repeated_work": {"true": "Yes: reads a Keychain entry, prompt file or config on every call; queries the same "
                              "rows twice in one call; rebuilds a constant dict or regex each call; loads the same "
                              "list the caller already loaded.",
                      "false": "No: all work depends on this call's arguments or on data that may have changed."},
}, "dup": scan.DUPLICATE}

# 4. literal, concrete conditions (TypeSafe: Jev is literal; state the exact condition)
V["literal"] = {"q": {
    "more_than_name": "Would describing everything function {id} does require more than one short sentence, "
                      "beyond what its name says?",
    "mixes_io_logic": "Does function {id} contain at least one call that reads or writes a file, database, network, "
                      "environment variable or subprocess, and also at least one if-statement or transformation "
                      "applied to that data?",
    "repeated_work": "Does function {id} perform an expensive step (file read, database query, network call, "
                     "subprocess, prompt load, or building a large constant) whose result does not depend on its "
                     "arguments, or perform the same query or read twice?",
}, "c": {}, "dup": "Could function {id} be deleted and replaced by calling another function in this file, "
                   "with no change in behavior?"}

# 5. code-measured facts added to the state (code measures, Jev judges)
V["facts"] = {"q": scan.QUESTIONS, "c": scan.CRITERIA, "dup": scan.DUPLICATE, "facts": True}

IO = re.compile(r"(read|write|open|load|query|fetch|execute|connect|post|get|request|run|environ|"
                r"subprocess|list_|select|insert|update|save|urlopen|security)", re.I)


def facts(fn, all_fns):
    calls = fn["calls"]
    io = sorted(c for c in calls if IO.search(c))
    tree = ast.parse(fn["code"].strip() if not fn["code"].startswith(" ") else "if 1:\n" + fn["code"])
    names = [n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
             for n in ast.walk(tree) if isinstance(n, ast.Call)]
    repeated = sorted({n for n in names if n and names.count(n) > 1 and IO.search(n)})
    return {"line_count": fn["lines"], "loop_count": fn["loops"], "io_like_calls": io,
            "io_like_calls_made_more_than_once": repeated,
            "called_by_in_file": sorted(f["name"] for f in all_fns if fn["name"] in f["calls"] and f is not fn)}


def build(variant, spec):
    q, c, dup = spec["q"], spec["c"], spec["dup"]
    reqs = []
    for name in FILES:
        path = ROOT / name
        fns = scan.functions(path)
        for f in fns:
            state = {"file": name, "function_id": f["id"], "function_name": f["name"], "code": f["code"],
                     "names_it_calls": f["calls"], "line_count": f["lines"]}
            if spec.get("facts"):
                state["measured"] = facts(f, fns)
            qs = {k: scan.noul(q[k].format(id=f["id"]), c.get(k)) for k in KEYS}
            reqs.append({"variant": variant, "mode": "function", "file": name, "ids": [f["id"]],
                         "state": state, "questions": qs})
        state = {"file": name, "functions": {f["id"]: {"name": f["name"], "code": f["code"]} for f in fns}}
        if spec.get("facts"):
            for f in fns:
                state["functions"][f["id"]]["measured"] = facts(f, fns)
        qs = {}
        for f in fns:
            for k in KEYS:
                qs["%s__%s" % (f["id"], k)] = scan.noul(q[k].format(id=f["id"]), c.get(k))
            qs["%s__duplicate" % f["id"]] = scan.noul(dup.format(id=f["id"]))
        qs["most_attention"] = {"type": "choice", "instructions": "Which single function in this file would most "
                                "benefit from being simplified or restructured?",
                                "criteria": dict({f["id"]: f["name"] for f in fns}, none="No function needs it")}
        reqs.append({"variant": variant, "mode": "file", "file": name, "ids": [f["id"] for f in fns],
                     "state": state, "questions": qs})
    return reqs


def score(results, ref):
    rows = {}
    for r in results:
        if "error" in r:
            continue
        for k, a in r["answers"].items():
            if k == "most_attention":
                rows[(r["variant"], "pick", r["file"])] = a["choice"]
                continue
            fid, q = (r["ids"][0], k) if r["mode"] == "function" else k.split("__")
            rows[(r["variant"], r["mode"], r["file"], fid, q)] = a["value"]
    table = []
    for v in V:
        for mode in ("function", "file"):
            for q in KEYS + ["duplicate"]:
                tp = fp = fn = tn = 0
                for f, rr in ref.items():
                    for x in rr["functions"]:
                        p = rows.get((v, mode, f, x["id"], q))
                        if p is None:
                            continue
                        p, t = p >= .5, x[q]
                        tp += p and t; fp += p and not t; fn += (not p) and t; tn += (not p) and not t
                if tp + fp + fn + tn:
                    table.append({"variant": v, "mode": mode, "question": q, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                                  "precision": round(tp / (tp + fp), 2) if tp + fp else None,
                                  "recall": round(tp / (tp + fn), 2) if tp + fn else None,
                                  "agreement": round((tp + tn) / (tp + fp + fn + tn), 2)})
        picks = sum(rows.get((v, "pick", f)) == rr["most_attention"] for f, rr in ref.items())
        table.append({"variant": v, "mode": "file", "question": "most_attention", "matches": picks, "of": len(ref)})
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    reqs = [r for v, spec in V.items() for r in build(v, spec)]
    for r in reqs:
        scan.client.body(r["state"], r["questions"])  # validates size and shape before any call
    print("%d requests across %d variants" % (len(reqs), len(V)))
    if not a.run:
        return
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        results = list(pool.map(scan.call, reqs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in results)
    errors = [r for r in results if "error" in r]
    (out / "RESULTS.json").write_text(json.dumps(results, indent=1))
    ref = json.loads((Path(__file__).parent / "run-01/REFERENCE.json").read_text())
    table = score(results, ref)
    (out / "SCORES.json").write_text(json.dumps(table, indent=1))
    print("done in %.1fs, cost $%.4f, errors %d" % (time.monotonic() - start, cost, len(errors)))
    for e in errors[:5]:
        print(" ", e["variant"], e["mode"], e["file"], e["error"])


if __name__ == "__main__":
    main()
