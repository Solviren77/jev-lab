"""Offline tests: a local mock Decisions endpoint stands in for Jev. No paid calls."""
import json
import os
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = tempfile.mkdtemp()
os.environ.update(JEVLAB_HOME=TMP, JEVLAB_API_KEY="test", JEVLAB_API="http://127.0.0.1:0")

from jevlab import categorize, client, extract, scenario, store  # noqa: E402

SEEN = []


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        SEEN.append(body)
        answers = {}
        for k, q in body["questions"].items():
            if q["type"] == "noul":
                answers[k] = {"type": "noul", "noul": 0.9 if "renew" in q["instructions"] else 0.4}
            elif q["type"] == "choice":
                first = next(iter(q["criteria"]))
                answers[k] = {"type": "choice", "choice": first, "probabilities": {first: 0.8}, "confidence": 0.8}
            else:
                answers[k] = {"type": "score", "score": len(q["criteria"]) - 1}
        out = json.dumps({"model": body["model"], "answers": answers,
                          "usage": {"input_tokens": 10, "output_tokens": 2, "cost": 1e-5}}).encode()
        self.send_response(200)
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


class Offline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        client.API = "http://127.0.0.1:%d" % cls.httpd.server_port

    def test_scenario_variables_and_documents(self):
        s = scenario.load(ROOT / "examples/contract-review.json")
        rec = scenario.run(s, variables={"party": "Northwind LLC"})
        self.assertEqual(rec["status"], "ok", rec.get("error"))
        sent = SEEN[-1]
        self.assertIn("Northwind LLC", sent["questions"]["party_indemnifies"]["instructions"])
        self.assertIn("sample-agreement.txt", sent["state"]["documents"])
        self.assertIn("auto_renews", rec["selected"])
        self.assertNotIn("party_indemnifies", rec["selected"])  # 0.4 < 0.7 threshold
        self.assertIn("party_indemnifies", rec["uncertain"])
        self.assertIn("governing_law=arizona", rec["selected"])
        self.assertEqual(rec["answers"]["risk"]["value"], 1.0)

    def test_undefined_variable(self):
        s = {"name": "x", "variables": {}, "documents": [], "state": {"a": 1},
             "questions": {"q": {"type": "noul", "instructions": "Is {{missing}} here?"}}}
        with self.assertRaises(client.JevError):
            scenario.run(s)

    def test_dry_run_makes_no_call(self):
        n = len(SEEN)
        rec = scenario.run(scenario.load(ROOT / "examples/contract-review.json"), dry_run=True)
        self.assertEqual(rec["status"], "dry-run")
        self.assertEqual(len(SEEN), n)

    def test_validation(self):
        with self.assertRaises(client.JevError):
            client.validate({"q": {"type": "choice", "instructions": "x", "criteria": {"only": "one"}}})
        with self.assertRaises(client.JevError):
            client.normalize({"answers": {}}, {"q": {"type": "noul", "instructions": "x"}})

    def test_extractors(self):
        d = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(d / "a.docx", "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:r><w:t>Hello &amp; docx</w:t></w:r></w:p></w:document>")
        self.assertEqual(extract.extract(d / "a.docx"), "Hello & docx")
        (d / "m.eml").write_text("From: a@b.c\nSubject: Invoice 42\nContent-Type: text/plain\n\nPlease pay by Friday.\n")
        text = extract.extract(d / "m.eml")
        self.assertIn("Subject: Invoice 42", text)
        self.assertIn("Please pay", text)

    def test_categorize_dedupes(self):
        d = Path(tempfile.mkdtemp())
        (d / "bill.txt").write_text("Your invoice is due; please renew.")
        (d / "notes.xyz").write_text("ignored type")
        profile = scenario.load(ROOT / "examples/document-sorter.json")
        profile["output_jsonl"] = str(d / "out.jsonl")
        first = list(categorize.batch(profile, [d]))
        self.assertEqual([Path(r["source"]).name for r in first], ["bill.txt"])
        self.assertEqual(SEEN[-1]["state"]["document"]["name"], "bill.txt")
        self.assertEqual(list(categorize.batch(profile, [d])), [])  # already done
        (d / "bill.txt").write_text("changed content")
        self.assertEqual(len(list(categorize.batch(profile, [d]))), 1)
        self.assertEqual(len((d / "out.jsonl").read_text().splitlines()), 2)
        self.assertTrue(store.recent(10, "categorize"))


if __name__ == "__main__":
    unittest.main()
