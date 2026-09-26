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

# Experiment 3: titration (13 narrow questions, 8 files, 128 functions)

One call per function with all 13 questions (examples-style definitions): 128 calls, 2.1 s, $0.0098.
Blind Claude key per file. Best yes-threshold per question by F1. "Yes" = key count of true cases.

| Question | Key yes | Jev avg on yes / no | Best threshold | Flagged | Precision | Recall | Tier |
|---|---|---|---|---|---|---|---|
| mixes_io_logic | 46 | 0.89 / 0.19 | 0.5 | 50 | 0.90 | 0.98 | Trust |
| logs_sensitive | 7 | 0.75 / 0.13 | 0.7 | 6 | 1.00 | 0.86 | Trust (small n) |
| broad_except | 2 | 0.89 / 0.08 | 0.2 | 3 | 0.67 | 1.00 | Trust (tiny n; also doable in code) |
| hardcoded_config | 26 | 0.59 / 0.22 | 0.5 | 28 | 0.75 | 0.81 | Usable |
| hidden_side_effect | 5 | 0.82 / 0.19 | 0.7 | 8 | 0.62 | 1.00 | Usable as a filter |
| more_than_name | 17 | 0.62 / 0.25 | 0.6 | 15 | 0.73 | 0.65 | Usable |
| swallows_errors | 6 | 0.85 / 0.11 | 0.5 | 12 | 0.50 | 1.00 | Usable as a filter |
| should_split | 14 | 0.70 / 0.32 | 0.6 | 22 | 0.55 | 0.86 | Usable as a filter |
| inconsistent_returns | 5 | 0.77 / 0.30 | 0.8 | 6 | 0.50 | 0.60 | Weak |
| repeated_io | 20 | 0.48 / 0.27 | 0.5 | 20 | 0.55 | 0.55 | Weak (needs cross-function tracing) |
| docstring_mismatch | 2 | 0.40 / 0.20 | – | – | 0.09 | – | Drop |
| over_engineered | 1 | 0.32 / 0.28 | – | – | 0.02 | – | Drop |
| misleading_name | 0 | – / 0.27 | – | 93 at 0.2 | – | – | Drop (no positives; over-flags) |

Caveats: rare categories have 1–7 positives, so their scores are fragile; the key is one Claude reviewer
per file (it disagreed with the experiment-1 key on some functions, e.g. operations_for).

# Calibration: what Jev's numbers mean (no new calls)

Experiment 3 answers (1,664 = 128 functions × 13 questions) grouped by Jev value, vs the blind key:

| Jev value | Answers | Actually yes (all 13) | Actually yes (8 kept) |
|---|---|---|---|
| 0.0–0.3 | 1,166 | 0–3% | 0–3% |
| 0.3–0.5 | 251 | 5–8% | 8–9% |
| 0.5–0.6 | 68 | 25% | 29% |
| 0.6–0.7 | 65 | 32% | 41% |
| 0.7–0.8 | 37 | 62% | 78% |
| 0.8–0.9 | 36 | 81% | 87% |
| 0.9–1.0 | 41 | 90% | 90% |

Dropped questions (misleading name, over-engineered, docstring mismatch): 0 true answers in any band.
Docket-49 flags checked by Claude: 0.5–0.6 56%, 0.6–0.7 71%, 0.7–0.8 73%, 0.8–0.9 90%, 0.9–1.0 91% confirmed.
Reading: below 0.5 is a reliable no; 0.5–0.7 overstates (a 0.6 is right about a third of the time on the
strict key); 0.8+ is right about 9 times in 10.
