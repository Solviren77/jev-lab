"""SQLite run log at ~/.jev-lab/runs.db (override with JEVLAB_HOME)."""
import json
import os
import sqlite3
import time
from pathlib import Path


def home():
    p = Path(os.environ.get("JEVLAB_HOME", "~/.jev-lab")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def db():
    c = sqlite3.connect(home() / "runs.db")
    c.execute("""create table if not exists runs(id integer primary key, at real, kind text, scenario text,
                 source text, source_sha256 text, status text, selected text, record text)""")
    c.execute("create index if not exists runs_source on runs(scenario, source_sha256)")
    return c


def save(record):
    with db() as c:
        cur = c.execute("insert into runs(at, kind, scenario, source, source_sha256, status, selected, record)"
                        " values(?,?,?,?,?,?,?,?)",
                        (time.time(), record["kind"], record["scenario"], record.get("source"),
                         record.get("source_sha256"), record["status"],
                         json.dumps(record.get("selected", [])), json.dumps(record)))
        return cur.lastrowid


def seen(scenario, sha):
    with db() as c:
        return c.execute("select 1 from runs where scenario=? and source_sha256=? and status in ('ok','error') limit 1",
                         (scenario, sha)).fetchone() is not None


def recent(limit=50, kind=None):
    q = "select id, at, kind, scenario, source, status, selected, record from runs"
    args = []
    if kind:
        q += " where kind=?"
        args.append(kind)
    with db() as c:
        rows = c.execute(q + " order by id desc limit ?", args + [limit]).fetchall()
    return [dict(json.loads(r[7]), id=r[0], at=r[1]) for r in rows]
