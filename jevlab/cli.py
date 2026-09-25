"""jevlab run | categorize | watch | serve | history | install-agent"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import categorize, scenario, store

ROOT = Path(__file__).resolve().parent.parent


def kv(items):
    out = {}
    for item in items or []:
        k, _, v = item.partition("=")
        if not _:
            raise SystemExit("--var expects name=value")
        out[k] = v
    return out


def show(rec, full=False):
    if full or rec["status"] == "dry-run":
        print(json.dumps(rec, indent=2))
        return
    print("#%s %s %s %s" % (rec.get("id", "-"), rec["status"], rec["scenario"], rec.get("source") or ""))
    if rec["status"] == "error":
        print("  error:", rec["error"])
        return
    for k, a in rec["answers"].items():
        detail = a.get("choice") or a.get("level") or ""
        print("  %-28s %5.2f  %s" % (k, a["value"] if a["value"] is not None else float("nan"), detail))
    print("  selected: %s" % ", ".join(rec["selected"]))
    if rec["uncertain"]:
        print("  uncertain: %s" % ", ".join(rec["uncertain"]))
    m = rec["meta"]
    print("  %ss  in=%s out=%s cost=%s" % (m["seconds"], m["input_tokens"], m["output_tokens"], m["cost"]))


def plist(profile, interval):
    label = "com.solviren77.jevlab." + Path(profile).stem
    args = [sys.executable, "-m", "jevlab", "watch", str(Path(profile).resolve()), "--interval", str(interval)]
    log = store.home() / (Path(profile).stem + ".log")
    return label, """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>%s</string>
<key>ProgramArguments</key><array>%s</array>
<key>WorkingDirectory</key><string>%s</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>%s</string><key>StandardErrorPath</key><string>%s</string>
</dict></plist>
""" % (label, "".join("<string>%s</string>" % a for a in args), ROOT, log, log)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="jevlab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a scenario once")
    r.add_argument("scenario")
    r.add_argument("--var", action="append", help="name=value (repeatable)")
    r.add_argument("--doc", action="append", help="add a document path (repeatable)")
    r.add_argument("--dry-run", action="store_true", help="build and print the request; no API call")
    r.add_argument("--json", action="store_true")
    c = sub.add_parser("categorize", help="categorize files/folders once (skips files already done)")
    c.add_argument("profile")
    c.add_argument("paths", nargs="+")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--force", action="store_true", help="re-run files already categorized")
    c.add_argument("--limit", type=int, help="stop after N files")
    w = sub.add_parser("watch", help="watch the profile's folders continuously")
    w.add_argument("profile")
    w.add_argument("--interval", type=int, default=30)
    s = sub.add_parser("serve", help="local web page")
    s.add_argument("--port", type=int, default=8765)
    h = sub.add_parser("history")
    h.add_argument("--limit", type=int, default=20)
    h.add_argument("--kind", choices=["scenario", "categorize"])
    i = sub.add_parser("agent-plist", help="print a launchd plist that runs `watch` in the background")
    i.add_argument("profile")
    i.add_argument("--interval", type=int, default=30)
    a = ap.parse_args(argv)

    if a.cmd == "run":
        show(scenario.run(scenario.load(a.scenario), kv(a.var), a.doc, dry_run=a.dry_run), a.json)
    elif a.cmd == "categorize":
        p = scenario.load(a.profile)
        n = 0
        for rec in categorize.batch(p, a.paths, a.dry_run, a.force, a.limit):
            show(rec)
            n += 1
        print("%d file(s) processed" % n, file=sys.stderr)
    elif a.cmd == "watch":
        categorize.watch(scenario.load(a.profile), a.interval, log=lambda m: print(m, flush=True))
    elif a.cmd == "serve":
        from . import server
        server.serve(a.port)
    elif a.cmd == "history":
        for rec in store.recent(a.limit, a.kind):
            print("#%d %s %-10s %-24s %s  %s" % (rec["id"], rec["status"], rec["kind"], rec["scenario"],
                  rec.get("source") or "", ", ".join(rec.get("selected") or [])))
    elif a.cmd == "agent-plist":
        label, text = plist(a.profile, a.interval)
        print(text)
        print("<!-- save to ~/Library/LaunchAgents/%s.plist, then: launchctl load -w <that file> -->" % label,
              file=sys.stderr)


if __name__ == "__main__":
    main()
