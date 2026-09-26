# Code scan experiment 1 (2026-09-26)

Jev (`typesafe/jev-1.13-20260917`) vs a blind Claude Opus answer key, on 78 functions in 5 docket-49 files
(`assistant.py`, `provider.py`, `matter_write.py`, `triage.py`, `workspace_actions.py` at 8f9a15e1).
83 Jev calls, 3.2 s, $0.0052. Run outputs (contain docket-49 source) stay local in `run-01/`.

| Question | Mode | Precision | Recall | Agreement |
|---|---|---|---|---|
| Does more than its name says | per function | 0.57 | 0.71 | 0.82 |
| Does more than its name says | whole file | 0.86 | 0.71 | 0.91 |
| Mixes I/O with decision logic | per function | 0.85 | 0.92 | 0.92 |
| Mixes I/O with decision logic | whole file | 0.80 | 0.96 | 0.91 |
| Redoes identical work every call | per function | 0.78 | 0.50 | 0.77 |
| Redoes identical work every call | whole file | 0.71 | 0.43 | 0.73 |
| Duplicates another function | whole file | 0 of 9 flags confirmed (key found none) | | 0.88 |

"Which function most needs restructuring?" (Choice over function ids): Jev matched the key in 5 of 5 files.

Caveats: one run; the key is a single Claude reviewer, not ground truth; threshold 0.5 untuned.
