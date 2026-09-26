"""Section 1: classify every function in a repo (what the code IS, not what's wrong with it).

Five Pick-one questions per function, one call each, all functions in parallel.
  python3 classify.py REPO --out DIR
Writes CLASSES.json (per function) and prints a map.
"""
import argparse
import collections
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scan

Q = {
    "role": ("What is the main role of function {id}?", {
        "request_handler": "Receives an HTTP/web request or routes it to other code",
        "business_logic": "Applies the application's rules and decisions to data it is given",
        "data_access": "Reads or writes the database or stored files and returns the data",
        "external_call": "Calls an outside service or API (email, calendar, cloud) other than an AI model",
        "ai_call": "Builds a prompt or question for an AI model, calls it, or handles its answer",
        "rendering": "Builds HTML, Markdown, text or other output for display",
        "validation": "Checks that input is well-formed or allowed and rejects bad input",
        "transformation": "Converts, parses, cleans or reshapes data without deciding anything",
        "configuration": "Reads settings, credentials or environment, or sets the program up",
        "test": "Tests or checks other code (unit test, smoke test, audit, fixture setup)",
        "script": "Command-line entry point or one-off script that runs steps in order",
        "utility": "Small general-purpose helper used by other code",
        "other": "None of these"}),
    "layer": ("Which layer of the application does function {id} belong to?", {
        "ui": "User interface: what the user sees or interacts with in the browser",
        "api": "The boundary between the browser and the server: routes, request and response handling",
        "domain": "Core application rules about matters, clients, email, deadlines and documents",
        "storage": "Persisting and loading data: database, files, caches",
        "integration": "Talking to outside systems: Google, email providers, AI model providers",
        "infrastructure": "Cross-cutting plumbing: tracing, logging, configuration, prompts, locking",
        "tooling": "Build, test, seed, audit or developer scripts, not the running application",
        "other": "None of these"}),
    "domain": ("Which area of a law-practice application is function {id} mainly about?", {
        "matters": "Legal matters, clients, parties, registers and matter records",
        "email": "Email reading, classification, drafting, sending or mail caching",
        "calendar": "Calendar events, scheduling, deadlines on a calendar",
        "documents": "Documents, attachments, PDFs, exports",
        "assistant": "The chat assistant: conversation turns, operations it can perform",
        "tasks_notes": "Tasks, notes, work records, dictation",
        "navigation": "Moving between pages, tabs and views",
        "intake": "New inquiries, intake routing and triage",
        "ai_platform": "Model providers, prompts, Jev questions, fidelity checks, generation guards",
        "observability": "Tracing, logging, audit trails, diagnostics",
        "testing": "Tests, smoke checks, audits and seed data",
        "general": "Not specific to any area",
        "other": "None of these"}),
    "sensitivity": ("What is the most sensitive kind of data function {id} handles?", {
        "none": "No real data: constants, configuration shapes, pure helpers on generic values",
        "app_data": "Ordinary application data: ids, page names, statuses, counts",
        "personal": "Personal data about people: names, contact details, children, addresses",
        "legal_content": "Legal or client content: email bodies, documents, case facts, attorney notes",
        "credentials": "Secrets: API keys, tokens, passwords, OAuth credentials",
        "other": "None of these"}),
    "effect": ("What is the strongest effect function {id} can have?", {
        "none": "Pure: returns a value, changes nothing",
        "reads": "Only reads data or calls read-only services",
        "writes_local": "Writes local files, the local database or in-memory state",
        "writes_external": "Changes something outside this machine: sends email, edits a calendar, posts to a service",
        "other": "None of these"}),
}


def questions(fid):
    return {k: {"type": "choice", "instructions": q.format(id=fid), "criteria": c} for k, (q, c) in Q.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    repo, out = Path(a.repo).expanduser(), Path(__file__).parent / a.out
    out.mkdir(exist_ok=True)
    files = subprocess.run(["git", "-C", str(repo), "ls-files", "*.py"], capture_output=True, text=True,
                           check=True).stdout.split()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    reqs = []
    for rel in files:
        try:
            fns = scan.functions(repo / rel)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for f in fns:
            reqs.append({"key": "%s::%s:%d" % (rel, f["name"], f["line"]), "file": rel, "name": f["name"],
                         "line": f["line"], "lines": f["lines"], "ids": [f["id"]], "mode": "function",
                         "state": {"file": rel, "function_id": f["id"], "function_name": f["name"],
                                   "code": f["code"], "names_it_calls": f["calls"]},
                         "questions": questions(f["id"])})
    start = time.monotonic()
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(scan.call, reqs))
    cost = sum((r.get("meta") or {}).get("cost") or 0 for r in res)
    rows = []
    for r in res:
        row = {k: r[k] for k in ("key", "file", "name", "line", "lines")}
        if "answers" in r:
            for k, x in r["answers"].items():
                row[k] = x["choice"]
                row[k + "_conf"] = round(x["confidence"], 2)
        else:
            row["error"] = r["error"]
        rows.append(row)
    meta = {"repo": str(repo), "head": head, "files": len(files), "functions": len(rows),
            "seconds": round(time.monotonic() - start, 1), "cost": round(cost, 4),
            "errors": sum("error" in r for r in rows)}
    (out / "CLASSES.json").write_text(json.dumps({"meta": meta, "functions": rows}, indent=1))
    print(json.dumps(meta))
    ok = [r for r in rows if "error" not in r]
    for k in Q:
        c = collections.Counter(r[k] for r in ok)
        low = sum(r[k + "_conf"] < .6 for r in ok)
        print("%-12s %s   (confidence < 0.6: %d)" % (k, ", ".join("%s %d" % kv for kv in c.most_common()), low))


if __name__ == "__main__":
    main()
