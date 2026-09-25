"""Scenarios: questions + variables + documents -> one Jev call -> stored run."""
import copy
import hashlib
import json
import re
from pathlib import Path

from . import client, extract, store

VAR = re.compile(r"\{\{?\s*([A-Za-z_][\w.-]*)\s*\}\}?")  # {name} or {{name}}


def fill(value, variables):
    if isinstance(value, str):
        def sub(m):
            if m.group(1) not in variables:
                raise client.JevError("Undefined variable {{%s}}" % m.group(1))
            return str(variables[m.group(1)])
        return VAR.sub(sub, value)
    if isinstance(value, list):
        return [fill(v, variables) for v in value]
    if isinstance(value, dict):
        return {fill(k, variables): fill(v, variables) for k, v in value.items()}
    return value


def load(path):
    s = json.loads(Path(path).expanduser().read_text("utf8"))
    s.setdefault("name", Path(path).stem)
    s.setdefault("variables", {})
    s.setdefault("documents", [])
    s.setdefault("state", {})
    s["_dir"] = str(Path(path).expanduser().resolve().parent)  # relative document paths resolve here
    return s


def build(scenario, variables=None, documents=None, texts=None):
    """Return (state, questions). `texts` are inline documents {name: text} (e.g. from the web page)."""
    s = copy.deepcopy(scenario)
    v = dict(s["variables"], **(variables or {}))
    docs = {}
    for p in list(s["documents"]) + list(documents or []):
        p = Path(fill(p, v)).expanduser()
        if not p.is_absolute() and s.get("_dir"):
            p = Path(s["_dir"]) / p
        docs[p.name] = extract.extract(p)
    docs.update(texts or {})
    state = dict(fill(s["state"], v))
    if v:
        state.setdefault("variables", v)
    if docs:
        state.setdefault("documents", docs)
    if not state:
        raise client.JevError("Scenario has no state: add documents, variables or state")
    return state, fill(s["questions"], v)


def decide(questions, answers):
    """Apply per-question policy: noul threshold (default 0.5), choice label, score level."""
    selected, uncertain = [], []
    for k, a in answers.items():
        q = questions[k]
        if a["type"] == "noul":
            if a["value"] >= q.get("threshold", 0.5):
                selected.append(k)
            if 0.3 <= a["value"] < 0.7:
                uncertain.append(k)
        elif a["type"] == "choice":
            if a.get("confidence") is not None and a["confidence"] < q.get("threshold", 0):
                uncertain.append(k)
            elif a["choice"] not in q.get("ignore", []):
                selected.append("%s=%s" % (k, a["choice"]))
        else:
            selected.append("%s=%s" % (k, q["criteria"][round(a["score"])]))
    return {"selected": selected, "uncertain": uncertain}


def run(scenario, variables=None, documents=None, texts=None, dry_run=False, source=None, kind="scenario"):
    state, questions = build(scenario, variables, documents, texts)
    request = client.body(state, questions)
    record = {"kind": kind, "scenario": scenario["name"], "source": source,
              "request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
              "request_bytes": len(json.dumps(request).encode()), "questions": questions}
    if dry_run:
        record.update(status="dry-run", request=request)
        return record
    try:
        answers, meta = client.ask(state, questions)
        record.update(status="ok", answers=answers, meta=meta, **decide(questions, answers))
    except client.JevError as e:
        record.update(status="error", error=str(e))
    record["id"] = store.save(record)
    return record
