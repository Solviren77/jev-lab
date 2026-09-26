"""Experiment 1: can Jev flag suboptimal Python functions, and does whole-file context help?

Modes (same three per-function yes/no questions in both):
  function: one call per function; state = that function + names it calls.
  file:     one call per file; state = every function keyed f1..fN; per-function
            questions for all functions in one call, plus a duplicate question and a
            file-level pick-one.
Code does the parsing and measuring; Jev only judges meaning.

  python3 scan.py FILE.py ... --out DIR [--run]   (without --run: build requests only)
"""
import argparse
import ast
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from jevlab import client  # noqa: E402

QUESTIONS = {
    "more_than_name": "Does function {id} do more than its name and docstring say it does?",
    "mixes_io_logic": "Does function {id} both read or write external data (files, network, database, "
                      "environment, subprocess) and also make decisions or transform that data?",
    "repeated_work": "Does function {id} redo, on every call, work whose result would be the same each time "
                     "(re-reading an unchanged file, re-parsing, rebuilding a constant object, re-fetching)?",
}
DUPLICATE = "Does function {id} do substantially the same job as another function in this file?"
CRITERIA = {
    "more_than_name": {"true": "It has responsibilities a reader would not expect from its name",
                       "false": "Everything it does is what the name and docstring suggest"},
    "mixes_io_logic": {"true": "It performs I/O and also contains decision logic about the data",
                       "false": "It only does I/O, or only computes on values it is given"},
    "repeated_work": {"true": "Some work inside it would produce the same result on every call",
                      "false": "Nothing it does is needlessly repeated across calls"},
}


def functions(path):
    src = Path(path).read_text()
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            code = "\n".join(lines[node.lineno - 1:node.end_lineno])
            calls = sorted({n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
                            for n in ast.walk(node) if isinstance(n, ast.Call)
                            and isinstance(n.func, (ast.Name, ast.Attribute))})
            loops = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))]
            out.append({"name": node.name, "line": node.lineno, "code": code,
                        "calls": calls, "lines": node.end_lineno - node.lineno + 1,
                        "loops": len(loops)})
    out.sort(key=lambda f: f["line"])
    for i, f in enumerate(out, 1):
        f["id"] = "f%d" % i
    return out


def noul(text, crit=None):
    q = {"type": "noul", "instructions": text}
    if crit:
        q["criteria"] = crit
    return q


def function_requests(path, fns):
    reqs = []
    for f in fns:
        state = {"file": str(path), "function_id": f["id"], "function_name": f["name"],
                 "code": f["code"], "names_it_calls": f["calls"], "line_count": f["lines"]}
        qs = {k: noul(t.format(id=f["id"]), CRITERIA[k]) for k, t in QUESTIONS.items()}
        reqs.append({"mode": "function", "file": str(path), "ids": [f["id"]], "state": state, "questions": qs})
    return reqs


def file_request(path, fns):
    state = {"file": str(path), "functions": {f["id"]: {"name": f["name"], "code": f["code"]} for f in fns}}
    qs = {}
    for f in fns:
        for k, t in QUESTIONS.items():
            qs["%s__%s" % (f["id"], k)] = noul(t.format(id=f["id"]), CRITERIA[k])
        qs["%s__duplicate" % f["id"]] = noul(DUPLICATE.format(id=f["id"]))
    qs["most_attention"] = {"type": "choice",
                            "instructions": "Which single function in this file would most benefit from being "
                                            "simplified or restructured?",
                            "criteria": dict({f["id"]: f["name"] for f in fns}, none="No function needs it")}
    if len(qs) > 100:
        raise SystemExit("%s: %d questions; split the file" % (path, len(qs)))
    return {"mode": "file", "file": str(path), "ids": [f["id"] for f in fns], "state": state, "questions": qs}


def call(req):
    try:
        answers, meta = client.ask(req["state"], req["questions"])
        return dict(req, answers=answers, meta=meta)
    except client.JevError as e:
        return dict(req, error=str(e))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    inventory, reqs = {}, []
    for p in a.files:
        fns = functions(p)
        inventory[p] = [{k: f[k] for k in ("id", "name", "line", "lines", "loops", "calls")} for f in fns]
        reqs += function_requests(p, fns) + [file_request(p, fns)]
    (out / "INVENTORY.json").write_text(json.dumps(inventory, indent=1))
    sizes = [len(json.dumps(client.body(r["state"], r["questions"]))) for r in reqs]
    print("%d requests, largest %d bytes, total %d bytes" % (len(reqs), max(sizes), sum(sizes)))
    if not a.run:
        (out / "REQUESTS.json").write_text(json.dumps(reqs, indent=1))
        return
    start = time.monotonic()
    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(call, reqs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in results)
    errors = [r for r in results if "error" in r]
    (out / "RESULTS.json").write_text(json.dumps(results, indent=1))
    print("done in %.1fs, cost $%.4f, errors %d" % (time.monotonic() - start, cost, len(errors)))
    for e in errors:
        print(" ", e["mode"], e["file"], e["ids"][:3], e["error"])


if __name__ == "__main__":
    main()
