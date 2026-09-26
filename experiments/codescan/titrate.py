"""Experiment 3: titrate which code problems Jev detects well.

A bank of narrow yes/no questions (examples-style definitions, the experiment-2 winner) is asked
about every function in 8 docket-49 files, one call per function with all questions. A blind
Claude key answers the same bank. `score` sweeps the yes-threshold per question.

  python3 titrate.py run --out run-03        # Jev calls
  python3 titrate.py key-inventory --out run-03
  python3 titrate.py score --out run-03      # needs run-03/KEY.json
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan

ROOT = Path.home() / "GitHub/Solviren77/docket-49/prototype"
FILES = ["assistant.py", "provider.py", "matter_write.py", "triage.py", "workspace_actions.py",
         "email_issues.py", "google_calendar.py", "jev_workflow.py"]

BANK = {
    "more_than_name": ("Does function {id} do more than its name and docstring say it does?",
        "Yes if a reader would be surprised: e.g. `post` that also fetches credentials, `check` that also writes "
        "records, one function dispatching many unrelated operations, or a long function doing validation, I/O, "
        "calls and formatting.",
        "No if every step serves the job the name states, even if the function is long."),
    "mixes_io_logic": ("Does function {id} both read or write external data and also make decisions about or "
                       "transform that data?",
        "Yes: queries a database then filters or builds output from the rows; reads a file then parses and "
        "decides; calls an API then branches on the response. Calling a helper that does I/O counts as I/O.",
        "No: only performs the I/O and returns it; or only computes on arguments it was given."),
    "swallows_errors": ("Does function {id} catch an exception and then continue without re-raising, logging or "
                        "reporting it?",
        "Yes: `except: pass`, `except Exception: return None`, or returning a default value so the caller cannot "
        "tell something failed.",
        "No: it re-raises, raises a clearer error, logs or records the failure, or has no try/except."),
    "broad_except": ("Does function {id} catch a broad exception type (bare `except`, `Exception`, "
                     "`BaseException`) where a specific one would do?",
        "Yes: `except Exception:` or bare `except:` around code whose expected failures are known.",
        "No: catches only specific exception classes, or has no try/except."),
    "hidden_side_effect": ("Does function {id} change something outside itself that its name does not suggest?",
        "Yes: a `get_`/`load_`/`check`/`build` function that also writes files or rows, mutates its arguments, "
        "sets globals, or sends a request that changes state.",
        "No: its only effects are the ones its name announces, or it is pure."),
    "misleading_name": ("Does the name of function {id} describe something different from what it actually does?",
        "Yes: `validate` that actually transforms, `list_x` that returns one item, `is_x` that returns a string.",
        "No: the name is accurate even if vague or incomplete."),
    "docstring_mismatch": ("Does the docstring or leading comment of function {id} disagree with its code?",
        "Yes: the docstring describes parameters, return values or behavior the code does not have.",
        "No: the docstring matches the code, or there is no docstring."),
    "should_split": ("Would function {id} be clearer as two or more separate functions?",
        "Yes: it contains clearly separable stages or branches that each do a distinct job, e.g. parse, then "
        "validate, then write, then format a reply, or a long if-chain of unrelated operations.",
        "No: it does one job, even if that job takes many lines."),
    "hardcoded_config": ("Does function {id} contain hard-coded values that belong in configuration?",
        "Yes: literal URLs, file paths, model names, API endpoints, email addresses, credentials, or tuning "
        "numbers written inline in the function.",
        "No: literals are intrinsic to the logic (e.g. 0, 1, empty string, format strings) or come from "
        "module constants or arguments."),
    "logs_sensitive": ("Does function {id} write sensitive data (keys, tokens, passwords, personal data, full "
                       "message bodies) to logs, traces, errors or files?",
        "Yes: puts a credential, email body or personal field into a log line, exception message or trace span.",
        "No: logs only identifiers, counts, hashes or non-sensitive status."),
    "inconsistent_returns": ("Does function {id} return different kinds of result on different paths?",
        "Yes: returns a dict on success but None or a string on failure; sometimes raises and sometimes returns "
        "an error value for the same kind of problem.",
        "No: every path returns the same kind of value, or it returns nothing."),
    "repeated_io": ("Does function {id} perform the same read, query or external call more than once in a "
                    "single call, or on every call when the result would not change?",
        "Yes: queries the same rows twice; reads the same prompt file, Keychain entry or config on every call; "
        "calls a list function repeatedly in a loop.",
        "No: every read depends on this call's arguments or on data that may have changed."),
    "over_engineered": ("Is function {id} more general or abstract than its current uses require?",
        "Yes: options, parameters, indirection layers or plug-in hooks that nothing uses; a factory that builds "
        "one thing.",
        "No: every parameter and branch is used."),
}
KEYS = list(BANK)


def questions(fid):
    return {k: {"type": "noul", "instructions": q.format(id=fid), "criteria": {"true": t, "false": f}}
            for k, (q, t, f) in BANK.items()}


def requests():
    reqs, inv = [], {}
    for name in FILES:
        fns = scan.functions(ROOT / name)
        inv[name] = [{"id": f["id"], "name": f["name"], "line": f["line"], "lines": f["lines"]} for f in fns]
        for f in fns:
            state = {"file": name, "function_id": f["id"], "function_name": f["name"], "code": f["code"],
                     "names_it_calls": f["calls"]}
            reqs.append({"file": name, "ids": [f["id"]], "mode": "function", "state": state,
                         "questions": questions(f["id"])})
    return reqs, inv


def run(out):
    reqs, inv = requests()
    (out / "INVENTORY.json").write_text(json.dumps(inv, indent=1))
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, reqs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    (out / "RESULTS.json").write_text(json.dumps(res, indent=1))
    print("%d functions, %d calls, %.1fs, $%.4f, errors %d" % (sum(map(len, inv.values())), len(res),
          time.monotonic() - start, cost, sum("error" in r for r in res)))


def score(out):
    res = json.loads((out / "RESULTS.json").read_text())
    key = json.loads((out / "KEY.json").read_text())
    pred = {(r["file"], r["ids"][0], k): a["value"] for r in res if "answers" in r for k, a in r["answers"].items()}
    truth = {(f, x["id"], k): x[k] for f, rr in key.items() for x in rr["functions"] for k in KEYS if k in x}
    rows = []
    for k in KEYS:
        items = [(pred[i], t) for i, t in truth.items() if i[2] == k and i in pred]
        pos = sum(t for _, t in items)
        best = None
        sweep = []
        for thr in (.2, .3, .4, .5, .6, .7, .8, .9):
            tp = sum(p >= thr and t for p, t in items); fp = sum(p >= thr and not t for p, t in items)
            fn = pos - tp
            prec = tp / (tp + fp) if tp + fp else None
            rec = tp / pos if pos else None
            f1 = 2 * prec * rec / (prec + rec) if prec and rec else 0
            sweep.append({"threshold": thr, "flagged": tp + fp, "tp": tp, "fp": fp, "fn": fn,
                          "precision": prec, "recall": rec, "f1": round(f1, 2)})
            if best is None or f1 > best["f1"]:
                best = sweep[-1]
        # separation: mean Jev value on key-yes vs key-no
        yes = [p for p, t in items if t]; no = [p for p, t in items if not t]
        rows.append({"question": k, "n": len(items), "key_yes": pos,
                     "mean_yes": round(sum(yes) / len(yes), 2) if yes else None,
                     "mean_no": round(sum(no) / len(no), 2) if no else None,
                     "best": best, "sweep": sweep})
    (out / "SCORES.json").write_text(json.dumps(rows, indent=1))
    print("%-20s %4s %4s  %5s %5s  %5s %4s %5s %5s %4s" % ("question", "n", "yes", "avgY", "avgN",
                                                            "thr", "flag", "prec", "rec", "f1"))
    for r in sorted(rows, key=lambda r: -r["best"]["f1"]):
        b = r["best"]
        print("%-20s %4d %4d  %5s %5s  %5.1f %4d %5s %5s %4.2f" % (
            r["question"], r["n"], r["key_yes"], r["mean_yes"], r["mean_no"], b["threshold"], b["flagged"],
            "%.2f" % b["precision"] if b["precision"] is not None else "-",
            "%.2f" % b["recall"] if b["recall"] is not None else "-", b["f1"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "bank"])
    ap.add_argument("--out", default="run-03")
    a = ap.parse_args()
    out = Path(__file__).parent / a.out
    out.mkdir(exist_ok=True)
    if a.cmd == "run":
        run(out)
    elif a.cmd == "score":
        score(out)
    else:
        json.dump({k: {"question": q, "yes": t, "no": f} for k, (q, t, f) in BANK.items()}, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
