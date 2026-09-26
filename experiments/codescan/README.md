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

# Experiment 2: five prompt variants (same files, same key)

All variants sent concurrently: 498 calls, 8.2 s, $0.031, 0 errors. `control` reruns the experiment-1 prompt
to show run-to-run movement (up to ±0.07 on a cell), so smaller differences are noise.

| Variant | Change |
|---|---|
| statement | Statements instead of questions |
| no_criteria | Instructions only, no yes/no definitions |
| examples | Concrete yes/no boundary examples in the criteria |
| literal | Reworded as literal, checkable conditions |
| facts | Code-measured facts (I/O-like calls, repeated calls, callers) added to the state |

Precision / recall vs the key (threshold 0.5):

| Variant | Mode | More than name | Mixes I/O + logic | Repeated work | Pick matches |
|---|---|---|---|---|---|
| control | function | 0.55 / 0.71 | 0.85 / 0.92 | 0.81 / 0.46 | |
| control | file | 0.92 / 0.71 | 0.80 / 0.96 | 0.62 / 0.36 | 5/5 |
| statement | function | 0.57 / 0.71 | 0.85 / 0.92 | 0.62 / 0.29 | |
| statement | file | 0.85 / 0.65 | 0.82 / 0.92 | 0.55 / 0.39 | 5/5 |
| no_criteria | function | 0.57 / 0.76 | 0.85 / 0.92 | 0.72 / 0.46 | |
| no_criteria | file | 0.73 / 0.65 | 0.79 / 0.92 | 0.83 / 0.36 | 5/5 |
| examples | function | 0.83 / 0.59 | 0.85 / 0.92 | 0.80 / 0.43 | |
| examples | file | 1.00 / 0.65 | 0.77 / 0.96 | 0.71 / 0.43 | 5/5 |
| literal | function | 0.24 / 1.00 | 0.85 / 0.88 | 0.80 / 0.29 | |
| literal | file | 0.23 / 1.00 | 0.84 / 0.84 | 0.67 / 0.29 | 5/5 |
| facts | function | 0.60 / 0.71 | 0.85 / 0.92 | 0.82 / 0.50 | |
| facts | file | 0.91 / 0.59 | 0.85 / 0.88 | 0.79 / 0.39 | 4/5 |

Duplicate: every variant flagged some, the key confirmed none.
