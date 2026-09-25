"""Text extraction. Jev accepts text/JSON only, so every document becomes a string here."""
import email
import email.policy
import html
import json
import re
import subprocess
import zipfile
from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".json", ".csv", ".pdf", ".docx", ".eml"}


def _strip_html(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _pdf(path):
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise ValueError("pdftotext failed (is poppler installed?)")
    if not r.stdout.strip():
        raise ValueError("PDF has no text layer (scanned?); OCR it first")
    return r.stdout


def _docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf8")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _eml(path):
    msg = email.message_from_bytes(Path(path).read_bytes(), policy=email.policy.default)
    head = "\n".join("%s: %s" % (h, msg[h]) for h in ("From", "To", "Cc", "Date", "Subject") if msg[h])
    part = msg.get_body(preferencelist=("plain", "html"))
    text = part.get_content() if part else ""
    if part and part.get_content_type() == "text/html":
        text = _strip_html(text)
    names = [p.get_filename() for p in msg.iter_attachments() if p.get_filename()]
    if names:
        head += "\nAttachments: " + ", ".join(names)
    return head + "\n\n" + text


def extract(path):
    path = Path(path).expanduser()
    ext = path.suffix.lower()
    if ext == ".pdf":
        text = _pdf(path)
    elif ext == ".docx":
        text = _docx(path)
    elif ext == ".eml":
        text = _eml(path)
    elif ext == ".json":
        text = json.dumps(json.loads(path.read_text("utf8")), indent=1)
    elif ext in SUPPORTED:
        text = path.read_text("utf8", errors="replace")
    else:
        raise ValueError("Unsupported file type: %s" % ext)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
