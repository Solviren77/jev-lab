# Jev Lab

Run scenarios against TypeSafe's Jev (`typesafe/jev-1.13-20260917`) through OpenRouter's Decisions API, and categorize documents on this Mac in the background. Python 3 stdlib only; PDF text needs `pdftotext` (poppler).

The API key is read from the macOS Keychain: service `jev-api-beast`, account `api-key-jev` (the same entry docket-49 uses). Override with `JEVLAB_KEYCHAIN_SERVICE` / `JEVLAB_KEYCHAIN_ACCOUNT`. Every real run is a paid call (about $0.0001 each); `--dry-run` / **Preview request** make none.

## Scenario files

```json
{
  "name": "contract-review",
  "variables": {"party": "Acme Corp"},
  "documents": ["docs/sample-agreement.txt", "~/Documents/lease.pdf"],
  "state": {"extra": "any JSON the questions should see"},
  "questions": {
    "auto_renews": {"type": "noul", "instructions": "Does it renew automatically?", "threshold": 0.7},
    "law": {"type": "choice", "instructions": "Which law governs?", "criteria": {"az": "Arizona", "de": "Delaware", "none": "No clause"}},
    "risk": {"type": "score", "instructions": "How locked-in is {{party}}?", "criteria": ["Low", "Moderate", "High"]}
  }
}
```

- `{{name}}` is replaced from `variables` (overridable per run) in questions, state and document paths.
- Documents (`.txt .md .json .csv .pdf .docx .eml`) are extracted to text and sent as `state.documents[filename]`. Relative paths resolve from the scenario file's folder.
- Results: Noul → P(yes), selected at `threshold` (default 0.5); Choice → option + probabilities (optional `threshold` on confidence, `ignore` list); Score → level. 0.3–0.7 Nouls are flagged uncertain. Thresholds are your policy, not calibrated accuracy.
- Requests over 100 KB are refused; split long documents.

## Use

```sh
python3 -m jevlab serve                      # http://127.0.0.1:8765
python3 -m jevlab run examples/contract-review.json --var party="Northwind LLC" --doc ~/file.pdf
python3 -m jevlab run examples/contract-review.json --dry-run
python3 -m jevlab categorize examples/document-sorter.json ~/Documents/Inbox --limit 5
python3 -m jevlab history
```

## Background categorization

A profile is a scenario with `watch.folders` (and optional `watch.extensions`, `output_jsonl`). Each file is sent as `state.document = {name, text}`. Files are identified by content hash, so each version is categorized once; failures are recorded and not retried (use `categorize --force`).

```sh
python3 -m jevlab watch examples/document-sorter.json          # foreground
python3 -m jevlab agent-plist examples/document-sorter.json > ~/Library/LaunchAgents/com.solviren77.jevlab.document-sorter.plist
launchctl load -w ~/Library/LaunchAgents/com.solviren77.jevlab.document-sorter.plist
```

Runs are logged to `~/.jev-lab/runs.db` (override `JEVLAB_HOME`); the web page's History shows them. Scenarios saved from the page go to `~/.jev-lab/scenarios/`.

## Tests

```sh
python3 -m unittest discover -s tests
```

Offline, against a local mock endpoint.
