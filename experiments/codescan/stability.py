"""Experiment 4: (a) run-to-run stability of the 13-question bank, 5 identical runs;
(b) rewrites of the two grey-zone questions, scored against the experiment-3 key.

  python3 stability.py --out run-05
"""
import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan
import titrate

REWRITES = {
    "should_split_v2": ("Does function {id} carry out two or more distinct jobs that could each be named and "
                        "tested on their own?",
        "Yes: e.g. it validates input AND loads files AND calls a model AND formats a reply; or it is a long "
        "if/elif chain where branches perform unrelated operations; or it has sections separated by comments "
        "like '# step 2'.",
        "No: it does one job, even if long or with many small steps serving that job; a dispatcher that only "
        "routes to other functions; a test or script `main` that runs steps in order."),
    "should_split_v3": ("Could function {id} be divided into smaller functions, each with a clear single purpose, "
                        "without passing lots of shared state between them?",
        "Yes: there are clean seams where one stage's output feeds the next (parse -> validate -> store -> "
        "reply), and each stage is at least several lines.",
        "No: the steps are tightly interleaved, the function is short (under ~25 lines), or splitting would "
        "just move lines around."),
    "hardcoded_config_v2": ("Does function {id} write, inline in its own body, a value that an operator might "
                            "reasonably need to change between environments or over time?",
        "Yes: a URL, host, port, file or directory path, model name, API endpoint, email address, time zone, "
        "timeout, size or rate limit, or retry count written as a literal inside the function.",
        "No: the value is referenced through a named constant, config, environment variable or argument; or "
        "the literal is part of the logic itself (0, 1, '', a format string, a dict key, an error message, a "
        "regex, an HTTP status code)."),
    "hardcoded_config_v3": ("Does function {id} contain a literal URL, file path, model name, time zone, port "
                            "or numeric limit?",
        "Yes: any such literal appears in the function body.",
        "No: none of those literals appear; values come from constants, config or arguments."),
}


def build():
    reqs = []
    for name in titrate.FILES:
        for f in scan.functions(titrate.ROOT / name):
            reqs.append({"file": name, "ids": [f["id"]], "mode": "function",
                         "state": {"file": name, "function_id": f["id"], "function_name": f["name"],
                                   "code": f["code"], "names_it_calls": f["calls"]}, "fid": f["id"]})
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="run-05")
    a = ap.parse_args()
    out = Path(__file__).parent / a.out
    out.mkdir(exist_ok=True)
    base = build()
    jobs = []
    for run in range(5):
        for r in base:
            jobs.append(dict(r, run=run, questions=titrate.questions(r["fid"])))
    for r in base:
        jobs.append(dict(r, run="rewrite", questions={k: {"type": "noul", "instructions": q.format(id=r["fid"]),
                    "criteria": {"true": t, "false": f}} for k, (q, t, f) in REWRITES.items()}))
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, jobs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    print("%d calls, %.1fs, $%.4f, errors %d" % (len(res), time.monotonic() - start, cost, sum("error" in r for r in res)))
    (out / "RESULTS.json").write_text(json.dumps(res))

    # (a) stability
    vals = {}
    for r in res:
        if r["run"] == "rewrite" or "answers" not in r:
            continue
        for k, x in r["answers"].items():
            vals.setdefault((r["file"], r["fid"], k), []).append(x["value"])
    spreads = [max(v) - min(v) for v in vals.values() if len(v) == 5]
    sds = [statistics.pstdev(v) for v in vals.values() if len(v) == 5]
    exact = sum(s == 0 for s in spreads)
    thr = {k: v[0] for k, v in __import__("pipeline").USE.items()}
    flips = sum(1 for (f, i, k), v in vals.items() if len(v) == 5 and k in thr
                and len({x >= thr[k] for x in v}) > 1)
    kept = sum(1 for (f, i, k), v in vals.items() if len(v) == 5 and k in thr)
    stab = {"answers": len(spreads), "identical_all_5": exact, "mean_sd": round(statistics.mean(sds), 3),
            "max_spread": round(max(spreads), 3),
            "spread_pct": {p: round(sorted(spreads)[int(len(spreads) * p / 100) - 1], 3) for p in (50, 90, 99)},
            "flag_flips_at_cutoff": flips, "flag_answers": kept}
    print("stability:", json.dumps(stab))

    # (b) rewrites vs key
    key = json.loads((Path(__file__).parent / "run-03/KEY.json").read_text())
    truth = {(f, x["id"]): x for f, rr in key.items() for x in rr["functions"]}
    base_vals = {(f, i, k): statistics.mean(v) for (f, i, k), v in vals.items()}
    rows = []
    for q, orig in [("should_split", "should_split"), ("should_split_v2", "should_split"),
                    ("should_split_v3", "should_split"), ("hardcoded_config", "hardcoded_config"),
                    ("hardcoded_config_v2", "hardcoded_config"), ("hardcoded_config_v3", "hardcoded_config")]:
        pts = []
        for r in res:
            if "answers" not in r or (r["run"] == "rewrite") != (q in REWRITES):
                continue
            if q not in r["answers"] or (r["run"] not in ("rewrite", 0)):
                continue
            pts.append((r["answers"][q]["value"], truth[(r["file"], r["fid"])][orig]))
        y = [v for v, t in pts if t]; n = [v for v, t in pts if not t]
        grey = sum(.3 <= v < .7 for v, _ in pts) / len(pts)
        best = max(((t, *pr(pts, t)) for t in (.3, .4, .5, .6, .7, .8)), key=lambda z: z[3])
        rows.append({"question": q, "avg_yes": round(statistics.mean(y), 2), "avg_no": round(statistics.mean(n), 2),
                     "grey_zone": round(grey, 2), "best_threshold": best[0], "precision": best[1],
                     "recall": best[2], "f1": best[3]})
    for r in rows:
        print(r)
    (out / "SUMMARY.json").write_text(json.dumps({"cost": cost, "stability": stab, "rewrites": rows}, indent=1))


def pr(pts, thr):
    tp = sum(v >= thr and t for v, t in pts); fp = sum(v >= thr and not t for v, t in pts)
    pos = sum(t for _, t in pts)
    p = tp / (tp + fp) if tp + fp else 0; r = tp / pos if pos else 0
    return round(p, 2), round(r, 2), round(2 * p * r / (p + r), 2) if p + r else 0


if __name__ == "__main__":
    main()
