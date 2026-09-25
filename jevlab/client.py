"""Jev transport: OpenRouter Decisions API, key from macOS Keychain. Never logs the key or error bodies."""
import json
import math
import os
import subprocess
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("JEVLAB_MODEL", "typesafe/jev-1.13-20260917")
API = os.environ.get("JEVLAB_API", "https://openrouter.ai/api/alpha/decisions")
MAX_BYTES = 100_000
MAX_QUESTIONS = 100
TYPES = {"noul", "choice", "score"}


class JevError(Exception):
    pass


def _key():
    if os.environ.get("JEVLAB_API_KEY"):  # for local mock servers only
        return os.environ["JEVLAB_API_KEY"]
    r = subprocess.run(["security", "find-generic-password",
                        "-s", os.environ.get("JEVLAB_KEYCHAIN_SERVICE", "jev-api-beast"),
                        "-a", os.environ.get("JEVLAB_KEYCHAIN_ACCOUNT", "api-key-jev"), "-w"],
                       capture_output=True, text=True, timeout=15)
    if r.returncode or not r.stdout.strip():
        raise JevError("Jev key not found in Keychain (set JEVLAB_KEYCHAIN_SERVICE/ACCOUNT)")
    return r.stdout.strip()


def validate(questions):
    if not isinstance(questions, dict) or not 1 <= len(questions) <= MAX_QUESTIONS:
        raise JevError("Need 1-%d questions" % MAX_QUESTIONS)
    for name, q in questions.items():
        if q.get("type") not in TYPES:
            raise JevError("%s: type must be noul, choice or score" % name)
        if not str(q.get("instructions", "")).strip():
            raise JevError("%s: instructions required" % name)
        if q["type"] == "choice" and not (isinstance(q.get("criteria"), dict) and len(q["criteria"]) >= 2):
            raise JevError("%s: choice needs criteria {option: description} with 2+ options" % name)
        if q["type"] == "score" and not (isinstance(q.get("criteria"), list) and len(q["criteria"]) >= 2):
            raise JevError("%s: score needs criteria [level0, level1, ...]" % name)


def body(state, questions):
    validate(questions)
    b = {"model": MODEL, "state": state, "questions": questions}
    size = len(json.dumps(b).encode())
    if size > MAX_BYTES:
        raise JevError("Request is %d bytes (limit %d); trim or split documents" % (size, MAX_BYTES))
    return b


def normalize(raw, questions):
    """Return {name: {type, value (0-1), choice?, probabilities?, score?, confidence?}}."""
    answers = raw.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise JevError("Jev returned missing or unexpected answers")
    out = {}
    for name, a in answers.items():
        t = questions[name]["type"]
        if t == "noul":
            v = a.get("noul")
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
                raise JevError("%s: invalid probability" % name)
            out[name] = {"type": t, "value": v}
        elif t == "choice":
            c = a.get("choice")
            if c not in questions[name]["criteria"]:
                raise JevError("%s: unknown choice" % name)
            out[name] = {"type": t, "choice": c, "value": a.get("confidence"),
                         "probabilities": a.get("probabilities", {}), "confidence": a.get("confidence")}
        else:
            s = a.get("score")
            top = len(questions[name]["criteria"]) - 1
            if not isinstance(s, int) or not 0 <= s <= top:
                raise JevError("%s: invalid score" % name)
            out[name] = {"type": t, "score": s, "value": s / top, "level": questions[name]["criteria"][s]}
    return out


def ask(state, questions):
    """One call. No retries. Returns (answers, meta)."""
    b = body(state, questions)
    req = urllib.request.Request(API, data=json.dumps(b).encode(), headers={
        "content-type": "application/json", "authorization": "Bearer " + _key()})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = json.load(r)
    except urllib.error.HTTPError as e:
        e.close()
        raise JevError("Jev HTTP %d" % e.code) from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise JevError("Jev transport or response failure") from None
    usage = raw.get("usage") or {}
    return normalize(raw, questions), {
        "model": raw.get("model", MODEL), "seconds": round(time.monotonic() - start, 3),
        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
        "cost": usage.get("cost"), "id": raw.get("id")}
