"""Experiment 12: learn how Jev reads the three noisy security questions, on fixed held-out data.

Data: higgins-workspace functions (heldout-higgins2/FUNCS.json) with the paid Sonnet key: exactly one real
problem in all application code (do_POST, state_change_unguarded); everything else is false.
Each variant changes only the prompt (question wording, criteria, preamble) — same facts, same functions.
Two-question variants (presence split) are combined in code.

  python3 learn_prompts.py --out heldout-higgins2
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan
import security_ai as S
import taint as T

HERE = Path(__file__).parent
REAL = ("app/server.py::do_POST:635", "state_change_unguarded")
QS = ["injection_string_build", "path_from_input", "state_change_unguarded"]
VALIDATED = ("the value is checked to be an integer, UUID, or to match a strict pattern before use; it is a "
             "hash of the input; it comes from a hard-coded constant or configuration; or it is looked up in a "
             "fixed set of allowed values")


def noul(text, yes=None, no=None):
    q = {"type": "noul", "instructions": text}
    if yes:
        q["criteria"] = {"true": yes, "false": no}
    return q


def orig(fid, pre=True):
    qs = {k: v for k, v in S.questions(fid, ["security"]).items() if k in QS}
    if pre:
        for q in qs.values():
            q["instructions"] = T.PREAMBLE + q["instructions"]
    return qs


VARIANTS = {
    "0_baseline": lambda fid: orig(fid),
    "1_no_preamble": lambda fid: orig(fid, pre=False),
    "2_validated_is_safe": lambda fid: {
        k: dict(v, criteria={"true": v["criteria"]["true"],
                             "false": v["criteria"]["false"] + " Also no when " + VALIDATED + "."})
        for k, v in orig(fid).items()},
    "3_attacker": lambda fid: {
        "injection_string_build": noul(
            "Could someone sending a request, email or document to this application choose text that ends up "
            "inside a SQL query, shell command, file path or HTML built by function %s, changing its meaning?" % fid,
            "Yes: attacker-chosen text is inserted into the query, command, path or markup with no parameters, "
            "escaping or validation anywhere on the way.",
            "No: " + VALIDATED + "; or the text is passed as a bound parameter, argument list or escaped value."),
        "path_from_input": noul(
            "Could someone sending a request, email or document to this application choose which file function "
            "%s opens, reads, writes or serves?" % fid,
            "Yes: attacker-chosen text decides the file path, with no containment or allowlist check on the way.",
            "No: " + VALIDATED + "; or the path is checked to stay inside an allowed directory."),
        "state_change_unguarded": noul(
            "Could a web page on another site make the browser cause function %s to change stored data?" % fid,
            "Yes: the data-changing request path has no exact origin check, token, or permission check, so a "
            "cross-site request could trigger it.",
            "No: an exact origin/host check, token or permission check applies on the path; or the function "
            "is not reachable from a request; or it only reads.")},
    "4_presence_split": lambda fid: {
        "uses_outside_value": noul(
            "Does function %s put a value that came from a request, email or document into a SQL query, shell "
            "command, file path or HTML string?" % fid),
        "value_neutralised": noul(
            "In function %s or the path facts, is that outside value made safe before use — bound as a parameter, "
            "escaped, " % fid + VALIDATED + "?"),
        "changes_data_from_request": noul(
            "Does function %s change stored data (write, update, delete, save) as part of handling a request?" % fid),
        "exact_origin_check": noul(
            "Is there an exact origin, host, token or permission check on the request path that reaches function "
            "%s (in its own code or the path facts)?" % fid)},
    "5_statement": lambda fid: {
        k: dict(v, instructions=v["instructions"].replace("Does function", "Function").replace("?", ".")
                .replace(" build ", " builds ").replace(" open, read, write or serve", " opens, reads, writes or "
                "serves").replace(" handle a", " handles a"))
        for k, v in orig(fid).items()},
}


def combine(name, ans):
    if name != "4_presence_split":
        return ans
    return {"injection_string_build": ans["uses_outside_value"] * (1 - ans["value_neutralised"]),
            "path_from_input": ans["uses_outside_value"] * (1 - ans["value_neutralised"]),
            "state_change_unguarded": ans["changes_data_from_request"] * (1 - ans["exact_origin_check"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="heldout-higgins2")
    a = ap.parse_args()
    out = HERE / a.out
    F = json.loads((out / "FUNCS.json").read_text())
    routed = [f for f in F.values() if "role" in f and "security" in S.route(f)]
    jobs = []
    for name, make in VARIANTS.items():
        for f in routed:
            jobs.append({"variant": name, "key": f["key"], "ids": [f["fid"]], "mode": "function",
                         "state": {"file": f["file"], "function_id": f["fid"], "function_name": f["name"],
                                   "code": f["code"], "path_facts": T.facts_for(f)},
                         "questions": make(f["fid"])})
    t = time.monotonic()
    with ThreadPoolExecutor(16) as p:
        res = list(p.map(scan.call, jobs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    print("%d functions x %d variants = %d calls, %.1fs, $%.4f, errors %d" % (
        len(routed), len(VARIANTS), len(res), time.monotonic() - t, cost, sum("error" in r for r in res)))
    cut = json.loads((HERE / "run-11/CUTOFFS.json").read_text())
    rows = []
    for name in VARIANTS:
        vals = {}
        for r in res:
            if r["variant"] == name and "answers" in r:
                for q, v in combine(name, {k: x["value"] for k, x in r["answers"].items()}).items():
                    vals[(r["key"], q)] = v
        row = {"variant": name}
        for q in QS:
            items = sorted(((v, k) for k, v in vals.items() if k[1] == q), reverse=True)
            row[q] = {"flags@0.5": sum(v >= .5 for v, _ in items), "flags@cutoff": sum(v >= cut[q] for v, _ in items),
                      "mean": round(sum(v for v, _ in items) / len(items), 3)}
        rv = vals.get(REAL)
        allv = sorted(vals.values(), reverse=True)
        row["real_value"] = round(rv, 3) if rv is not None else None
        row["real_rank_all"] = allv.index(rv) + 1 if rv is not None else None
        sc = sorted((v for k, v in vals.items() if k[1] == REAL[1]), reverse=True)
        row["real_rank_in_question"] = sc.index(rv) + 1 if rv is not None else None
        rows.append(row)
    (out / "LEARN.json").write_text(json.dumps(rows, indent=1))
    print("%-22s %-22s %-22s %-22s %s" % ("variant", "string-built @.5/@cut", "path @.5/@cut", "state @.5/@cut",
                                          "real item: value, rank in its question / overall"))
    for r in rows:
        print("%-22s %-22s %-22s %-22s %s, %s/%s" % (r["variant"],
              "%d / %d" % (r[QS[0]]["flags@0.5"], r[QS[0]]["flags@cutoff"]),
              "%d / %d" % (r[QS[1]]["flags@0.5"], r[QS[1]]["flags@cutoff"]),
              "%d / %d" % (r[QS[2]]["flags@0.5"], r[QS[2]]["flags@cutoff"]),
              r["real_value"], r["real_rank_in_question"], r["real_rank_all"]))


if __name__ == "__main__":
    main()
