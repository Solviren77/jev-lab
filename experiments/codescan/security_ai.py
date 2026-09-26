"""Experiment 5: security and AI question sets, routed by the section-1 classification.

  python3 security_ai.py run   --out run-07   # Jev calls on routed application functions
  python3 security_ai.py batches --out run-07 # key batches for reviewers
  python3 security_ai.py score --out run-07   # needs KEY_A/B/C.json (3 reviewers, majority vote)
"""
import argparse
import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan

REPO = Path.home() / "GitHub/Solviren77/docket-49"
TOOL = re.compile(r"(prototype/build/|^tests/|^experiments/|^docs/|^tools/|^bin/|^nudge/)")

SECURITY = {
    "injection_string_build": ("Does function {id} build a SQL query, shell command, file path or HTML/JS string by "
                               "inserting variable values into text?",
        "Yes: f-strings, % formatting, + or .format used to put values into SQL, a subprocess command string, "
        "an HTML fragment or a path; including `shell=True` with a formatted string.",
        "No: SQL uses ? or named parameters; subprocess gets a list of arguments; HTML values go through an "
        "escaping function; paths are built with Path joins of trusted constants only."),
    "path_from_input": ("Does function {id} open, read, write or serve a file whose name or path comes from a "
                        "request, a message or other outside input?",
        "Yes: a filename, id or path taken from the URL, request body, email or model output is used to open or "
        "serve a file.",
        "No: all paths are fixed constants or derived only from internal values."),
    "path_checked": ("If function {id} uses an outside-supplied file name or path, does it check that the result "
                     "stays inside an allowed directory or matches an allowlist before using it?",
        "Yes: it resolves the path and checks it is under a base directory, rejects '..', or matches a strict "
        "pattern or allowlist; or it uses no outside-supplied path at all.",
        "No: an outside-supplied name reaches open/read/serve without such a check."),
    "state_change_unguarded": ("Does function {id} handle a request that changes data without checking where the "
                               "request came from or that the caller is allowed?",
        "Yes: a POST/PATCH/DELETE handler or mutation endpoint with no origin, token, session or permission check "
        "in it or clearly applied before it.",
        "No: it checks origin, a token or permissions; or it does not handle incoming requests; or it only reads."),
    "secret_inline": ("Does function {id} contain a secret written in the code?",
        "Yes: an API key, token, password, client secret or private key appears as a literal.",
        "No: secrets are read from Keychain, environment or a credential store; placeholder names are not secrets."),
    "sends_data_out": ("Does function {id} send application data to a service outside this machine?",
        "Yes: posts email content, matter data, documents or prompts to Google, an AI provider, a tracing "
        "backend or any other remote API.",
        "No: it only works locally, or only fetches data without sending application content."),
}
AI = {
    "ai_output_unvalidated": ("Does function {id} use an AI model's answer without checking its structure or "
                              "allowed values first?",
        "Yes: model output is parsed and used directly (fields read, text shown or saved, actions taken) with no "
        "schema check, allowed-value check or type check.",
        "No: output is validated against a schema, allowlist or expected type before use; or the function does "
        "not handle model output."),
    "prompt_includes_untrusted": ("Does function {id} put untrusted text (emails, documents, user messages, web "
                                  "content) into a prompt for an AI model?",
        "Yes: email bodies, attachments, user-typed requests or fetched content are inserted into a prompt or "
        "model input.",
        "No: the prompt contains only trusted, fixed or application-generated content; or it builds no prompt."),
    "untrusted_separated": ("If function {id} puts untrusted text into a prompt, is that text clearly separated "
                            "from the instructions?",
        "Yes: untrusted content goes in a separate message, a labelled data field, delimiters or structured "
        "state, and instructions say to treat it as data; or no untrusted text is used.",
        "No: untrusted text is concatenated into the instruction text itself."),
    "ai_no_size_limit": ("Does function {id} send content to an AI model without limiting its size?",
        "Yes: documents, emails or histories are sent with no truncation, length check or token budget.",
        "No: content is truncated, capped, counted or checked against a limit before sending; or it sends "
        "nothing to a model."),
    "ai_model_inline": ("Does function {id} write an AI model name, temperature or token limit inline?",
        "Yes: a literal like 'claude-...', 'gpt-...', a model id, temperature or max_tokens number appears in "
        "the function body.",
        "No: model settings come from constants, configuration or arguments."),
    "ai_failure_unhandled": ("Does function {id} call an AI model without handling the call failing or returning "
                             "an unusable answer?",
        "Yes: a timeout, HTTP error, refusal or malformed answer would crash the request or be used as if valid, "
        "with no fallback, error message or retry.",
        "No: failures are caught and reported, retried, or turned into a clear error; or it makes no model call."),
}
SETS = {"security": SECURITY, "ai": AI}


def route(row):
    sets = []
    if (row["role"] in ("request_handler", "data_access", "external_call", "validation", "configuration")
            or row["sensitivity"] in ("legal_content", "personal", "credentials")
            or row["effect"] == "writes_external"):
        sets.append("security")
    if row["role"] == "ai_call" or row["domain"] == "ai_platform":
        sets.append("ai")
    return sets


def questions(fid, names):
    qs = {}
    for s in names:
        for k, (q, t, f) in SETS[s].items():
            qs[k] = {"type": "noul", "instructions": q.format(id=fid), "criteria": {"true": t, "false": f}}
    return qs


def run(out):
    classes = json.loads((Path(__file__).parent / "run-06/CLASSES.json").read_text())["functions"]
    cls = {r["key"]: r for r in classes if "error" not in r and not TOOL.search(r["file"])}
    code = {}
    for rel in sorted({r["file"] for r in cls.values()}):
        for f in scan.functions(REPO / rel):
            code["%s::%s:%d" % (rel, f["name"], f["line"])] = f
    reqs = []
    for k, r in cls.items():
        sets = route(r)
        if not sets or k not in code:
            continue
        f = code[k]
        reqs.append({"key": k, "file": r["file"], "sets": sets, "ids": [f["id"]], "mode": "function",
                     "state": {"file": r["file"], "function_id": f["id"], "function_name": f["name"],
                               "code": f["code"], "names_it_calls": f["calls"]},
                     "questions": questions(f["id"], sets)})
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, reqs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    slim = [{"key": r["key"], "file": r["file"], "sets": r["sets"], "fid": r["ids"][0],
             "jev": {k: round(a["value"], 3) for k, a in r.get("answers", {}).items()}, "error": r.get("error")}
            for r in res]
    (out / "RESULTS.json").write_text(json.dumps(slim, indent=1))
    n_sec = sum("security" in r["sets"] for r in res); n_ai = sum("ai" in r["sets"] for r in res)
    print("%d of %d app functions routed (security %d, ai %d); %.1fs, $%.4f, errors %d" % (
        len(res), len(cls), n_sec, n_ai, time.monotonic() - start, cost, sum(bool(r.get("error")) for r in res)))


def batches(out):
    res = json.loads((out / "RESULTS.json").read_text())
    by = {}
    for r in res:
        by.setdefault(r["file"], []).append({"key": r["key"], "sets": r["sets"]})
    files = sorted(by, key=lambda f: -len(by[f]))
    groups, sizes = [[], [], []], [0, 0, 0]
    for f in files:
        i = sizes.index(min(sizes)); groups[i].append(f); sizes[i] += len(by[f])
    (out / "KEY_BATCHES.json").write_text(json.dumps([{f: by[f] for f in g} for g in groups], indent=1))
    bank = {s: {k: {"question": q, "yes": t, "no": f} for k, (q, t, f) in SETS[s].items()} for s in SETS}
    (out / "BANK.json").write_text(json.dumps(bank, indent=1))
    print("batch sizes", sizes)


def score(out):
    res = {r["key"]: r for r in json.loads((out / "RESULTS.json").read_text())}
    keys = [json.loads((out / ("KEY_%s.json" % x)).read_text()) for x in "ABC"]
    votes = {}
    for kf in keys:
        for fn in kf:
            for q, v in fn["answers"].items():
                votes.setdefault((fn["key"], q), []).append(bool(v))
    rows = []
    for s, bank in SETS.items():
        for q in bank:
            pts, agree_all, n = [], 0, 0
            for (k, qq), vs in votes.items():
                if qq != q or len(vs) != 3 or k not in res or q not in res[k]["jev"]:
                    continue
                n += 1
                agree_all += len(set(vs)) == 1
                pts.append((res[k]["jev"][q], sum(vs) >= 2, len(set(vs)) == 1))
            if not pts:
                continue
            pos = sum(t for _, t, _ in pts)
            sweep = []
            for thr in (.3, .4, .5, .6, .7, .8):
                tp = sum(v >= thr and t for v, t, _ in pts); fp = sum(v >= thr and not t for v, t, _ in pts)
                p = tp / (tp + fp) if tp + fp else 0; r = tp / pos if pos else 0
                sweep.append((thr, tp + fp, round(p, 2), round(r, 2), round(2 * p * r / (p + r), 2) if p + r else 0))
            best = max(sweep, key=lambda z: z[4])
            y = [v for v, t, _ in pts if t]; nn = [v for v, t, _ in pts if not t]
            rows.append({"set": s, "question": q, "n": n, "key_yes": pos,
                         "reviewers_unanimous": round(agree_all / n, 2),
                         "avg_yes": round(statistics.mean(y), 2) if y else None,
                         "avg_no": round(statistics.mean(nn), 2) if nn else None,
                         "best_threshold": best[0], "flagged": best[1], "precision": best[2], "recall": best[3],
                         "f1": best[4]})
    (out / "SCORES.json").write_text(json.dumps(rows, indent=1))
    print("%-9s %-26s %4s %4s %6s %5s %5s %4s %4s %5s %5s %4s" % ("set", "question", "n", "yes", "unanim",
          "avgY", "avgN", "thr", "flag", "prec", "rec", "f1"))
    for r in rows:
        print("%-9s %-26s %4d %4d %6.0f%% %5s %5s %4.1f %4d %5.2f %5.2f %4.2f" % (r["set"], r["question"], r["n"],
              r["key_yes"], r["reviewers_unanimous"] * 100, r["avg_yes"], r["avg_no"], r["best_threshold"],
              r["flagged"], r["precision"], r["recall"], r["f1"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "batches", "score"])
    ap.add_argument("--out", default="run-07")
    a = ap.parse_args()
    out = Path(__file__).parent / a.out
    out.mkdir(exist_ok=True)
    {"run": run, "batches": batches, "score": score}[a.cmd](out)


if __name__ == "__main__":
    main()
