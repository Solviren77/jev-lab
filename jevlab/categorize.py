"""Categorize files with a scenario profile; optionally watch folders and do it continuously."""
import hashlib
import json
import time
from pathlib import Path

from . import extract, scenario, store


def files(paths, extensions):
    exts = {e.lower() for e in extensions} if extensions else extract.SUPPORTED
    for p in paths:
        p = Path(p).expanduser()
        items = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
        for f in items:
            if f.suffix.lower() in exts and not any(part.startswith(".") for part in f.parts[-3:]):
                yield f


def one(profile, path, dry_run=False, force=False):
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if not force and not dry_run and store.seen(profile["name"], sha):
        return None
    try:
        text = extract.extract(path)
    except Exception as e:  # extraction failures are recorded, not retried
        rec = {"kind": "categorize", "scenario": profile["name"], "source": str(path),
               "source_sha256": sha, "status": "error", "error": "extract: %s" % e}
        rec["id"] = store.save(rec)
        return rec
    p = dict(profile, state=dict(profile.get("state", {}), document={"name": path.name, "text": text}))
    rec = scenario.run(p, dry_run=dry_run, source=str(path), kind="categorize")
    if not dry_run:
        rec["source_sha256"] = sha
        with store.db() as c:
            c.execute("update runs set source_sha256=?, record=? where id=?", (sha, json.dumps(rec), rec["id"]))
        out = profile.get("output_jsonl")
        if out:
            with open(Path(out).expanduser(), "a") as fh:
                fh.write(json.dumps({"file": str(path), "status": rec["status"], "selected": rec.get("selected"),
                                     "uncertain": rec.get("uncertain"), "error": rec.get("error")}) + "\n")
    return rec


def batch(profile, paths, dry_run=False, force=False, limit=None):
    done = []
    for f in files(paths, profile.get("watch", {}).get("extensions")):
        if limit is not None and len(done) >= limit:
            break
        rec = one(profile, f, dry_run, force)
        if rec:
            done.append(rec)
            yield rec


def watch(profile, interval=30, settle=5, log=print):
    folders = profile.get("watch", {}).get("folders")
    if not folders:
        raise SystemExit("Profile has no watch.folders")
    log("watching %s every %ss" % (", ".join(folders), interval))
    while True:
        now = time.time()
        for f in files(folders, profile["watch"].get("extensions")):
            try:
                if now - f.stat().st_mtime < settle:
                    continue  # still being written
                rec = one(profile, f)
            except OSError:
                continue
            if rec:
                log("%s  %s  %s" % (rec["status"], f, ", ".join(rec.get("selected") or []) or rec.get("error", "")))
        time.sleep(interval)
