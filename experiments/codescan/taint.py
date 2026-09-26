"""Experiment 6: taint pass (code) + rerun of the security/AI questions with path facts.

Stage 1 (code, deterministic):
  - call graph over application code (by callee name; approximate)
  - sources: HTTP entry points (do_GET/POST/PATCH/DELETE), inbound mail/Workspace reads, model output
  - reachability from each source kind, with the shortest call chain
  - guards found in the chain: host/origin check, path containment, error handling in callers
  - sink facts in the function itself: parameterised SQL, list-form subprocess, shell=True, file opens
Stage 2 (Jev): same questions as experiment 5, now with a `path_facts` block in the state.
Stage 3: score experiment-5 (no facts) vs this run against "real after whole-path review"
         (3-reviewer majority AND the severity review's `real`).

  python3 taint.py graph  --out run-08
  python3 taint.py run    --out run-08
  python3 taint.py score  --out run-08
"""
import argparse
import ast
import collections
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan
import security_ai as S

HERE = Path(__file__).parent
REQ = re.compile(r"^do_(GET|POST|PATCH|DELETE|PUT)$")
MAIL_CALLS = {"inbox", "message", "thread", "attachment", "_get", "sync", "_sync", "list_google_mail",
              "email_read", "email_search", "workspace_inbox"}
MODEL_CALLS = {"run", "claude", "codex", "agent", "ask", "_call", "generate"}
MODEL_MODULES = ("provider", "jev", "guarded_generation", "matter_chat", "email_issues", "matter_update")


def calls_in(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else None
            if name:
                out.append((base, name, n))
    return out


def sink_facts(fn_node, src):
    facts = []
    for base, name, n in calls_in(fn_node):
        if name in ("execute", "executemany") and n.args:
            a = n.args[0]
            if isinstance(a, ast.JoinedStr) or (isinstance(a, ast.BinOp) and isinstance(a.op, (ast.Mod, ast.Add))) \
                    or (isinstance(a, ast.Call) and getattr(a.func, "attr", "") == "format"):
                seg = ast.get_source_segment(src, a) or ""
                only_q = bool(re.fullmatch(r"[^{}%]*(\{[^}]*(\?|placeholders|qs|marks)[^}]*\}|%s)[^{}%]*", seg)) \
                    and "?" in seg or "'?'" in seg or '"?"' in seg
                facts.append("SQL text built with formatting" + (" (only '?' placeholders inserted)" if only_q else ""))
            elif len(n.args) > 1:
                facts.append("SQL uses bound parameters")
        if base == "subprocess" or name in ("run", "Popen", "check_output", "call") and base == "subprocess":
            shell = any(k.arg == "shell" and getattr(k.value, "value", False) for k in n.keywords)
            listy = n.args and isinstance(n.args[0], (ast.List, ast.Tuple))
            facts.append("subprocess with shell=True" if shell else
                         "subprocess with an argument list (no shell)" if listy else "subprocess call")
        if name in ("open", "read_text", "read_bytes", "write_text", "write_bytes"):
            facts.append("opens/reads/writes a file")
    return sorted(set(facts))


def graph(out):
    classes = json.loads((HERE / "run-06/CLASSES.json").read_text())["functions"]
    app = {r["key"]: r for r in classes if "error" not in r and not S.TOOL.search(r["file"])}
    funcs, by_name = {}, collections.defaultdict(list)
    for rel in sorted({r["file"] for r in app.values()}):
        src = (S.REPO / rel).read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = "%s::%s:%d" % (rel, node.name, node.lineno)
                if key not in app:
                    continue
                code = ast.get_source_segment(src, node) or ""
                calls = calls_in(node)
                funcs[key] = {"key": key, "file": rel, "name": node.name, "module": Path(rel).stem,
                              "callees": sorted({c for _, c, _ in calls}),
                              "calls_raw": sorted({"%s.%s" % (b, c) if b else c for b, c, _ in calls}),
                              "host_origin_check": bool(re.search(r"_trusted_host|[Oo]rigin", code)),
                              "containment_check": bool(re.search(r"\.resolve\(\)", code) and
                                                        re.search(r"parents|is_relative_to|relative_to", code)),
                              "catches": sorted(set(re.findall(r"except\s*\(?\s*([\w., ]+)", code))),
                              "sinks": sink_facts(node, src)}
                by_name[node.name].append(key)
    callers = collections.defaultdict(set)
    for k, f in funcs.items():
        for c in f["callees"]:
            for tgt in by_name.get(c, []):
                if tgt != k:
                    callers[tgt].add(k)
    # sources
    src = {"http_request": [k for k, f in funcs.items() if REQ.match(f["name"])],
           "inbound_mail": [k for k, f in funcs.items() if f["module"] in ("google_gmail", "workspace_reads")
                            and f["name"] in MAIL_CALLS],
           "model_output": [k for k, f in funcs.items() if f["module"] in MODEL_MODULES and f["name"] in MODEL_CALLS]}
    # forward reachability over callees (data flows into callees as arguments) for http;
    # for mail/model the data flows back to CALLERS (return values), then onward to their callees.
    reach = {k: {} for k in funcs}
    for kind, starts in src.items():
        seen, frontier = {}, [(s, [funcs[s]["name"]]) for s in starts]
        if kind != "http_request":
            nxt = []
            for s, chain in frontier:
                for c in callers[s]:
                    nxt.append((c, [funcs[c]["name"]] + chain))
            frontier += nxt
        while frontier:
            k, chain = frontier.pop(0)
            if k in seen or len(chain) > 6:
                continue
            seen[k] = chain
            for c in funcs[k]["callees"]:
                for tgt in by_name.get(c, []):
                    if tgt not in seen:
                        frontier.append((tgt, chain + [funcs[tgt]["name"]]))
        for k, chain in seen.items():
            reach[k][kind] = chain
    names_to_keys = by_name
    for k, f in funcs.items():
        chains = reach[k]
        chain_keys = set()
        for chain in chains.values():
            for n in chain:
                chain_keys.update(names_to_keys.get(n, []))
        f["reached_from"] = {kind: " -> ".join(ch) for kind, ch in chains.items()}
        f["guards_on_path"] = sorted({g for ck in chain_keys | {k}
                                      for g, on in (("host/origin check", funcs[ck]["host_origin_check"]),
                                                    ("path containment check", funcs[ck]["containment_check"]))
                                      if on and ck in funcs})
        f["callers"] = sorted(funcs[c]["name"] for c in callers[k])[:12]
        f["callers_catch"] = sorted({e for c in callers[k] for e in funcs[c]["catches"]})[:12]
    (out / "GRAPH.json").write_text(json.dumps({"sources": src, "functions": funcs}, indent=1))
    n = collections.Counter(kind for f in funcs.values() for kind in f["reached_from"])
    print("%d functions; sources: %s; reachable: %s; unreachable from any source: %d" % (
        len(funcs), {k: len(v) for k, v in src.items()}, dict(n),
        sum(not f["reached_from"] for f in funcs.values())))


def facts_for(f):
    return {
        "reached_from_outside_input": f["reached_from"] or "not reachable from any HTTP request, inbound mail or "
                                                           "model output",
        "protections_on_that_path": f["guards_on_path"] or ["none found"],
        "callers": f["callers"] or ["no callers in application code"],
        "exceptions_caught_by_callers": f["callers_catch"] or ["none"],
        "sink_facts_in_this_function": f["sinks"] or ["none"],
        "note": "Facts come from static analysis of the whole codebase and may be incomplete.",
    }


PREAMBLE = ("Use the path_facts: a problem only counts if outside input can actually reach it and no protection "
            "on the path or in the callers already handles it. ")


def run(out):
    G = json.loads((out / "GRAPH.json").read_text())["functions"]
    prev = json.loads((HERE / "run-07/RESULTS.json").read_text())
    reqs = []
    for r in prev:
        f = G.get(r["key"])
        if not f:
            continue
        fn = next(x for x in scan.functions(S.REPO / r["file"]) if x["id"] == r["fid"])
        qs = S.questions(r["fid"], r["sets"])
        for q in qs.values():
            q["instructions"] = PREAMBLE + q["instructions"]
        reqs.append({"key": r["key"], "file": r["file"], "sets": r["sets"], "ids": [r["fid"]], "mode": "function",
                     "state": {"file": r["file"], "function_id": r["fid"], "function_name": fn["name"],
                               "code": fn["code"], "path_facts": facts_for(f)},
                     "questions": qs})
    t = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, reqs))
    cost = sum((x.get("meta") or {}).get("cost") or 0 for x in res)
    slim = [{"key": x["key"], "file": x["file"], "sets": x["sets"], "fid": x["ids"][0],
             "jev": {k: round(a["value"], 3) for k, a in x.get("answers", {}).items()}, "error": x.get("error")}
            for x in res]
    (out / "RESULTS.json").write_text(json.dumps(slim, indent=1))
    print("%d calls, %.1fs, $%.4f, errors %d" % (len(res), time.monotonic() - t, cost,
                                                 sum(bool(x.get("error")) for x in res)))


PROBLEM = ["injection_string_build", "path_from_input", "state_change_unguarded", "ai_output_unvalidated",
           "ai_model_inline", "ai_failure_unhandled", "ai_no_size_limit"]


def truth():
    keys = [json.loads((HERE / ("run-07/KEY_%s.json" % x)).read_text()) for x in "ABC"]
    votes = collections.defaultdict(list)
    for kf in keys:
        for fn in kf:
            for q, v in fn["answers"].items():
                votes[(fn["key"], q)].append(bool(v))
    sev = json.loads((HERE / "run-07/SEVERITY.json").read_text())
    real = {}
    for s in sev:
        k = s["key"]
        if "|" in k:
            fk, q = k.split("|", 1)
        elif "#" in k:
            fk, q = k.split("#", 1)
        elif k.count("::") == 2:
            fk, q = k.rsplit("::", 1)
        else:
            fk, q = k, s["finding"]
        real[(fk, q)] = s["real"]
    t = {}
    for (k, q), v in votes.items():
        if q in PROBLEM and len(v) == 3:
            maj = sum(v) >= 2
            t[(k, q)] = maj and real.get((k, q), real.get((k, None), True))
    # findings the severity pass assessed per function without naming the question
    for (fk, q), r in real.items():
        if q in PROBLEM:
            t[(fk, q)] = bool(r) and t.get((fk, q), False) or (bool(r) and (fk, q) in t)
    return t


def score(out):
    T = truth()
    old = {(r["key"], q): v for r in json.loads((HERE / "run-07/RESULTS.json").read_text()) for q, v in r["jev"].items()}
    new = {(r["key"], q): v for r in json.loads((out / "RESULTS.json").read_text()) for q, v in r["jev"].items()}
    rows = []
    for q in PROBLEM:
        items = [(k, t) for k, t in T.items() if k[1] == q and k in old and k in new]
        if not items:
            continue
        pos = sum(t for _, t in items)
        row = {"question": q, "n": len(items), "real": pos}
        for label, pred in (("old", old), ("new", new)):
            best = None
            for thr in (.3, .4, .5, .6, .7, .8, .9):
                tp = sum(pred[k] >= thr and t for k, t in items); fp = sum(pred[k] >= thr and not t for k, t in items)
                p = tp / (tp + fp) if tp + fp else 0; r = tp / pos if pos else 0
                f1 = 2 * p * r / (p + r) if p + r else 0
                cand = (round(f1, 2), thr, tp + fp, round(p, 2), round(r, 2))
                if best is None or cand[0] > best[0]:
                    best = cand
            fl5 = sum(pred[k] >= .5 for k, _ in items)
            row[label] = {"f1": best[0], "thr": best[1], "flagged": best[2], "precision": best[3], "recall": best[4],
                          "flagged_at_0.5": fl5,
                          "avg_real": round(sum(pred[k] for k, t in items if t) / pos, 2) if pos else None,
                          "avg_not": round(sum(pred[k] for k, t in items if not t) / (len(items) - pos), 2)}
        rows.append(row)
    (out / "SCORES.json").write_text(json.dumps(rows, indent=1))
    print("%-24s %4s %4s | %-34s | %-34s" % ("question", "n", "real", "OLD f1 thr flag prec rec (@.5)",
                                             "NEW f1 thr flag prec rec (@.5)"))
    for r in rows:
        f = lambda d: "%4.2f %.1f %4d %4.2f %4.2f (%3d) %s/%s" % (d["f1"], d["thr"], d["flagged"], d["precision"],
                                                                 d["recall"], d["flagged_at_0.5"], d["avg_real"],
                                                                 d["avg_not"])
        print("%-24s %4d %4d | %s | %s" % (r["question"], r["n"], r["real"], f(r["old"]), f(r["new"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["graph", "run", "score"])
    ap.add_argument("--out", default="run-08")
    a = ap.parse_args()
    out = HERE / a.out
    out.mkdir(exist_ok=True)
    {"graph": graph, "run": run, "score": score}[a.cmd](out)


if __name__ == "__main__":
    main()
