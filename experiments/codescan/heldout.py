"""Experiment 11: held-out test. The docket-49-tuned pipeline, unchanged in questions, cutoffs and filters,
run on another repository. Nothing here is specific to the target repo.

Stages: classify every function -> route security/AI questions -> generic call graph + path facts
(sources auto-detected) -> per-question cutoffs from run-11 -> nested "can't point to a line" filter.
Outputs FLAGS.json (kept) and DROPPED.json (first-pass flags the line filter removed) for review.

  python3 heldout.py ~/GitHub/Solviren77/higgins-workspace --out heldout-higgins
"""
import argparse
import ast
import collections
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import classify as C
import nested as N
import scan
import security_ai as S
import taint as T

HERE = Path(__file__).parent
TOOLING = re.compile(r"(^|/)(tests?|spikes?|scripts?|docs?|examples?|fixtures?|build|bin)/|(^|/)test_|_test\.py$|conftest")
MODEL_HINT = re.compile(r"anthropic|openai|openrouter|/v1/messages|chat\.completions|messages\.create|"
                        r"api/alpha/decisions|claude-|gpt-")
ROUTE_DECOR = re.compile(r"\.(route|get|post|put|patch|delete|websocket)$")


def pool(fn, items):
    with ThreadPoolExecutor(16) as p:
        return list(p.map(fn, items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    repo, out = Path(a.repo).expanduser(), HERE / a.out
    out.mkdir(exist_ok=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    files = [f for f in subprocess.run(["git", "-C", str(repo), "ls-files", "*.py"], capture_output=True, text=True,
                                       check=True).stdout.split() if not TOOLING.search(f)]
    t0 = time.monotonic(); cost = 0.0

    # ---- stage 1: parse + classify
    funcs, srcs = {}, {}
    for rel in files:
        try:
            src = (repo / rel).read_text(); tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        srcs[rel] = src
        ids = {(f["name"], f["line"]): f for f in scan.functions(repo / rel)}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (node.name, node.lineno) in ids:
                f = ids[(node.name, node.lineno)]
                key = "%s::%s:%d" % (rel, node.name, node.lineno)
                code = ast.get_source_segment(src, node) or ""
                calls = T.calls_in(node)
                decos = [ast.unparse(d.func if isinstance(d, ast.Call) else d) for d in node.decorator_list]
                funcs[key] = {"key": key, "file": rel, "name": node.name, "module": Path(rel).stem, "fid": f["id"],
                              "code": f["code"], "calls": f["calls"], "callees": sorted({c for _, c, _ in calls}),
                              "calls_raw": sorted({"%s.%s" % (b, c) if b else c for b, c, _ in calls}),
                              "http_entry": bool(T.REQ.match(node.name) or any(ROUTE_DECOR.search(d) for d in decos)),
                              "model_call": bool(MODEL_HINT.search(code)),
                              "host_origin_check": bool(re.search(r"_trusted_host|[Oo]rigin|csrf|CSRF", code)),
                              "containment_check": bool(re.search(r"\.resolve\(\)", code) and
                                                        re.search(r"parents|is_relative_to|relative_to", code)),
                              "catches": sorted(set(re.findall(r"except\s*\(?\s*([\w., ]+)", code))),
                              "sinks": T.sink_facts(node, src), "own_protections": T.own_protections(code, node)}
    jobs = [{"key": k, "ids": [f["fid"]], "mode": "function",
             "state": {"file": f["file"], "function_id": f["fid"], "function_name": f["name"], "code": f["code"],
                       "names_it_calls": f["calls"]}, "questions": C.questions(f["fid"])} for k, f in funcs.items()]
    for r in pool(scan.call, jobs):
        cost += (r.get("meta") or {}).get("cost") or 0
        if "answers" in r:
            funcs[r["key"]].update({q: x["choice"] for q, x in r["answers"].items()})
    print("%s @ %s: %d app files, %d functions classified" % (repo.name, head, len(srcs), len(funcs)))

    # ---- stage 2: generic graph
    by_name = collections.defaultdict(list)
    for k, f in funcs.items():
        by_name[f["name"]].append(k)
    def resolve(cur):
        res = []
        for raw in funcs[cur]["calls_raw"]:
            base, _, c = raw.rpartition(".")
            cands = by_name.get(c, [])
            if base:
                mod = [t for t in cands if funcs[t]["module"] == base]
                cands = mod or ([] if base not in ("self", "cls") else [t for t in cands if funcs[t]["file"] == funcs[cur]["file"]])
            elif len(cands) > 1:
                cands = [t for t in cands if funcs[t]["file"] == funcs[cur]["file"]]
            if len(cands) == 1:
                res.append(cands[0])
        return res
    callers = collections.defaultdict(set)
    for k in funcs:
        for t in resolve(k):
            if t != k:
                callers[t].add(k)
    sources = {"http_request": [k for k, f in funcs.items() if f["http_entry"]],
               "model_output": [k for k, f in funcs.items() if f["model_call"]]}
    reach = {k: {} for k in funcs}
    for kind, starts in sources.items():
        frontier = [(s, [funcs[s]["name"]]) for s in starts]
        if kind == "model_output":
            frontier += [(c, [funcs[c]["name"], funcs[s]["name"]]) for s in starts for c in callers[s]]
        seen = {}
        while frontier:
            k, chain = frontier.pop(0)
            if k in seen or len(chain) > 6:
                continue
            seen[k] = chain
            frontier += [(t, chain + [funcs[t]["name"]]) for t in resolve(k) if t not in seen]
        for k, ch in seen.items():
            reach[k][kind] = ch
    def subtree(start, depth=3):
        seen, fr, prot = {start}, [(start, 0)], set(funcs[start]["own_protections"])
        while fr:
            cur, d = fr.pop(0)
            if d >= depth:
                continue
            for t in resolve(cur):
                if t not in seen:
                    seen.add(t); prot |= set(funcs[t]["own_protections"]); fr.append((t, d + 1))
        return seen, sorted(prot)
    reaches_model = {k: any(funcs[t]["model_call"] for t in subtree(k)[0]) for k in funcs}
    for k, f in funcs.items():
        chain_keys = {kk for ch in reach[k].values() for n in ch for kk in by_name.get(n, [])} | {k}
        f["reached_from"] = {kind: " -> ".join(ch) for kind, ch in reach[k].items()}
        f["guards_on_path"] = sorted({g for ck in chain_keys for g, on in
                                      (("host/origin check", funcs[ck]["host_origin_check"]),
                                       ("path containment check", funcs[ck]["containment_check"])) if on})
        f["callers"] = sorted(funcs[c]["name"] for c in callers[k])[:12]
        f["callers_catch"] = sorted({e for c in callers[k] for e in funcs[c]["catches"]})[:12]
        found = collections.defaultdict(set)
        for t in subtree(k)[0] - {k}:
            for p in funcs[t]["own_protections"]:
                found[p].add(funcs[t]["name"])
        f["downstream_protections"] = {p: sorted(n)[:6] for p, n in found.items()}
        f["model_calls_via"] = {funcs[t]["name"]: subtree(t)[1] or ["none"] for t in resolve(k) if reaches_model[t]}
    print("sources: %s; reachable: %s" % ({k: len(v) for k, v in sources.items()},
          dict(collections.Counter(kind for f in funcs.values() for kind in f["reached_from"]))))

    # ---- stage 3: routed questions with path facts, tuned cutoffs
    cut = json.loads((HERE / "run-11/CUTOFFS.json").read_text())
    jobs = []
    for k, f in funcs.items():
        if "role" not in f:
            continue
        sets = S.route(f)
        if not sets:
            continue
        qs = S.questions(f["fid"], sets)
        for q in qs.values():
            q["instructions"] = T.PREAMBLE + q["instructions"]
        jobs.append({"key": k, "ids": [f["fid"]], "mode": "function",
                     "state": {"file": f["file"], "function_id": f["fid"], "function_name": f["name"],
                               "code": f["code"], "path_facts": T.facts_for(f)}, "questions": qs})
    first = []
    for r in pool(scan.call, jobs):
        cost += (r.get("meta") or {}).get("cost") or 0
        for q, x in r.get("answers", {}).items():
            if q in cut and x["value"] >= cut[q]:
                first.append((r["key"], q, round(x["value"], 3)))
    print("routed %d functions; %d first-pass flags" % (len(jobs), len(first)))

    # ---- stage 4: nested line filter (anchor questions for absence problems)
    jobs = []
    for k, q, v in first:
        f = funcs[k]
        lines = N.numbered(f["code"])
        lines = dict(list(lines.items())[:250])
        instr = (N.ANCHOR[q].replace("Which line", "Which line of function " + f["name"]) if q in N.ANCHOR else
                 "Which line of function %s shows this problem: %s?" % (f["name"], N.DESC[q])) + " Choose none if no line does."
        jobs.append({"key": k, "q": q, "v": v, "ids": [f["fid"]], "mode": "function",
                     "state": {"file": f["file"], "function_name": f["name"], "path_facts": T.facts_for(f)},
                     "questions": {"line": {"type": "choice", "instructions": instr,
                                            "criteria": dict(lines, none="No line in this function shows the problem")}}})
    kept, dropped = [], []
    for r in pool(scan.call, jobs):
        cost += (r.get("meta") or {}).get("cost") or 0
        line = r.get("answers", {}).get("line", {}).get("choice", "?")
        row = {"key": r["key"], "question": r["q"], "first_pass": r["v"], "line": line,
               "line_text": N.numbered(funcs[r["key"]]["code"]).get(line, ""),
               "path_facts": T.facts_for(funcs[r["key"]])}
        (dropped if line == "none" else kept).append(row)
    (out / "FLAGS.json").write_text(json.dumps(kept, indent=1))
    (out / "DROPPED.json").write_text(json.dumps(dropped, indent=1))
    (out / "META.json").write_text(json.dumps({"repo": str(repo), "head": head, "functions": len(funcs),
                                               "first_pass": len(first), "kept": len(kept), "dropped": len(dropped),
                                               "cost": round(cost, 4), "seconds": round(time.monotonic() - t0, 1)}, indent=1))
    print("kept %d, dropped %d; total %.1fs, $%.4f" % (len(kept), len(dropped), time.monotonic() - t0, cost))
    print(json.dumps(collections.Counter(r["question"] for r in kept)))


if __name__ == "__main__":
    main()
