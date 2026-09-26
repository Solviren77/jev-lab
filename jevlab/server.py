"""Local web page for editing and running scenarios. Binds 127.0.0.1 only."""
import base64
import json
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import client, extract, scenario, store

ROOT = Path(__file__).resolve().parent.parent
PAGE = Path(__file__).with_name("page.html")
NAME = re.compile(r"^[\w.-]{1,80}$")


def dirs():
    user = store.home() / "scenarios"
    user.mkdir(exist_ok=True)
    return [user, ROOT / "examples"]


def listing():
    seen, out = set(), []
    for d in dirs():
        for f in sorted(d.glob("*.json")):
            if f.stem not in seen:
                seen.add(f.stem)
                try:
                    title = json.loads(f.read_text("utf8")).get("title", "")
                except ValueError:
                    title = ""
                out.append({"name": f.stem, "path": str(f), "editable": d == dirs()[0], "title": title})
    return out


def find(name):
    for d in dirs():
        if (d / (name + ".json")).exists():
            return d / (name + ".json")
    raise FileNotFoundError(name)


def uploads(items):
    """[{name, base64}] -> {name: text}; binary types are extracted via a temp file."""
    out = {}
    for u in items or []:
        name = Path(u["name"]).name
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / name
            p.write_bytes(base64.b64decode(u["base64"]))
            out[name] = extract.extract(p)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj, ctype="application/json"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/scenarios":
            return self.send(200, listing())
        if self.path.startswith("/api/scenario/"):
            name = self.path.rsplit("/", 1)[1]
            if not NAME.match(name):
                return self.send(400, {"error": "bad name"})
            try:
                return self.send(200, scenario.load(find(name)))
            except FileNotFoundError:
                return self.send(404, {"error": "not found"})
        if self.path.startswith("/api/runs"):
            kind = "categorize" if "kind=categorize" in self.path else "scenario" if "kind=scenario" in self.path else None
            return self.send(200, store.recent(100, kind))
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("origin") not in (None, "http://127.0.0.1:%d" % self.server.server_port,
                                             "http://localhost:%d" % self.server.server_port):
            return self.send(403, {"error": "cross-origin request refused"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            if self.path == "/api/save":
                s = {k: v for k, v in body["scenario"].items() if k != "_dir"}
                if not NAME.match(s.get("name", "")):
                    raise client.JevError("Name: letters, digits, dot, dash, underscore")
                (dirs()[0] / (s["name"] + ".json")).write_text(json.dumps(s, indent=2) + "\n")
                return self.send(200, {"saved": s["name"]})
            if self.path == "/api/compare":
                texts = dict(body.get("texts") or {}, **uploads(body.get("uploads")))
                names = [n for n in body.get("names", []) if NAME.match(n)]
                if not 2 <= len(names) <= 10:
                    raise client.JevError("Pick 2 to 10 saved scenarios to compare")
                def one(n):
                    s = scenario.load(find(n))
                    if texts:
                        s["documents"] = []  # compare on the documents given here
                    return scenario.run(s, texts=texts or None)
                with ThreadPoolExecutor(len(names)) as pool:
                    return self.send(200, list(pool.map(one, names)))
            if self.path in ("/api/run", "/api/preview"):
                s = body["scenario"]
                s.setdefault("name", "untitled")
                for k in ("variables", "state"):
                    s.setdefault(k, {})
                s.setdefault("documents", [])
                rec = scenario.run(s, texts=dict(body.get("texts") or {}, **uploads(body.get("uploads"))),
                                   dry_run=self.path == "/api/preview")
                return self.send(200, rec)
        except (client.JevError, ValueError, KeyError, OSError) as e:
            return self.send(400, {"error": str(e)})
        self.send(404, {"error": "not found"})


def serve(port=8765):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Jev Lab on http://127.0.0.1:%d" % port, flush=True)
    httpd.serve_forever()
