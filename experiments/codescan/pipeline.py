"""Code-health pipeline over a repository (experiment 3's tuned questions).

Stage 1 (code): parse every function; detect repeated I/O-like calls deterministically.
Stage 2 (Jev):  one call per function with the 8 questions that tested usable, each with its tuned threshold.
Stage 3:        rank functions by weighted flags -> RANKED.json for Claude confirmation.

  python3 pipeline.py REPO --out DIR [--run]
"""
import argparse
import ast
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan
import titrate

# question -> (threshold, weight, tier)
USE = {
    "mixes_io_logic": (.5, 1, "trust"),
    "logs_sensitive": (.7, 3, "trust"),
    "broad_except": (.5, 1, "trust"),
    "hardcoded_config": (.5, 1, "usable"),
    "more_than_name": (.6, 2, "usable"),
    "hidden_side_effect": (.7, 2, "filter"),
    "swallows_errors": (.5, 2, "filter"),
    "should_split": (.6, 2, "filter"),
}
IO = re.compile(r"(read|write|open|load|query|fetch|execute|connect|post|request|urlopen|environ|subprocess|"
                r"list_|select|insert|update|save|security|get_)", re.I)
SKIP = re.compile(r"(^|/)(test_|tests?/|.*_test\.py$)")


def repeated_io(code):
    try:
        tree = ast.parse("if 1:\n" + code if code.startswith((" ", "\t")) else code)
    except SyntaxError:
        return []
    names = [n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
             for n in ast.walk(tree) if isinstance(n, ast.Call)]
    return sorted({n for n in names if n and IO.search(n) and names.count(n) > 1})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    repo, out = Path(a.repo).expanduser(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = [f for f in subprocess.run(["git", "-C", str(repo), "ls-files", "*.py"], capture_output=True,
                                       text=True, check=True).stdout.split() if not SKIP.search(f)]
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    reqs, funcs, skipped = [], {}, []
    qs_all = titrate.questions("{id}")
    for rel in files:
        try:
            fns = scan.functions(repo / rel)
        except (SyntaxError, UnicodeDecodeError) as e:
            skipped.append((rel, str(e)[:80]))
            continue
        for f in fns:
            key = "%s::%s:%d" % (rel, f["name"], f["line"])
            funcs[key] = {"file": rel, "name": f["name"], "line": f["line"], "lines": f["lines"],
                          "code_repeated_io": repeated_io(f["code"])}
            if f["lines"] < 3:
                continue  # one-liners: nothing to judge
            state = {"file": rel, "function_id": f["id"], "function_name": f["name"], "code": f["code"],
                     "names_it_calls": f["calls"]}
            qs = {k: dict(qs_all[k], instructions=qs_all[k]["instructions"].replace("{id}", f["id"])) for k in USE}
            reqs.append({"key": key, "file": rel, "ids": [f["id"]], "mode": "function", "state": state, "questions": qs})
    ok = []
    for r in reqs:
        try:
            scan.client.body(r["state"], r["questions"])
            ok.append(r)
        except scan.client.JevError as e:
            skipped.append((r["key"], str(e)[:80]))
    print("%s @ %s: %d files, %d functions, %d Jev calls, %d skipped" % (repo.name, head, len(files), len(funcs),
                                                                         len(ok), len(skipped)))
    if not a.run:
        return
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, ok))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    errors = [r for r in res if "error" in r]
    for r in res:
        if "answers" not in r:
            continue
        f = funcs[r["key"]]
        f["jev"] = {k: round(a["value"], 2) for k, a in r["answers"].items()}
        f["flags"] = [k for k, (thr, _, _) in USE.items() if f["jev"][k] >= thr]
        f["score"] = sum(USE[k][1] for k in f["flags"]) + (2 if f["code_repeated_io"] else 0)
    ranked = sorted((dict(v, key=k) for k, v in funcs.items() if v.get("score")), key=lambda x: (-x["score"], -x["lines"]))
    meta = {"repo": str(repo), "head": head, "files": len(files), "functions": len(funcs), "jev_calls": len(ok),
            "seconds": round(time.monotonic() - start, 1), "cost": round(cost, 4), "errors": len(errors),
            "skipped": skipped, "thresholds": {k: v[0] for k, v in USE.items()}}
    (out / "RANKED.json").write_text(json.dumps({"meta": meta, "ranked": ranked}, indent=1))
    counts = {k: sum(k in x.get("flags", []) for x in funcs.values()) for k in USE}
    counts["code_repeated_io"] = sum(bool(x["code_repeated_io"]) for x in funcs.values())
    print("%.1fs, $%.4f, errors %d; %d functions flagged" % (meta["seconds"], cost, len(errors), len(ranked)))
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
