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

# Experiment 4: stability and grey-zone rewrites (768 calls, 12.2 s, $0.055)

Stability, 5 identical runs of the 13-question bank on 128 functions (1,664 answers each run):
identical in all 5 runs 14%; median spread 0.01; 90% of answers within 0.05; 99% within 0.09; worst 0.16;
mean standard deviation 0.008. Of 1,024 answers to the 8 kept questions, 17 (1.7%) crossed their cutoff in
some runs and not others.

Rewrites (scored against the experiment-3 key; avg Jev value on key-yes / key-no, share in 0.3–0.7):

| Question | Avg yes | Avg no | Grey zone | Best cutoff | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| should_split (original) | 0.70 | 0.32 | 48% | 0.7 | 0.80 | 0.57 | 0.67 |
| should_split_v2 (distinct nameable jobs, with exclusions) | 0.74 | 0.27 | 34% | 0.5 | 0.52 | 1.00 | 0.68 |
| should_split_v3 (clean seams, ≥ several lines each) | 0.77 | 0.32 | 33% | 0.7 | 0.65 | 0.93 | 0.76 |
| hardcoded_config (original) | 0.59 | 0.22 | 36% | 0.5 | 0.69 | 0.77 | 0.73 |
| hardcoded_config_v2 (operator might change it) | 0.61 | 0.19 | 20% | 0.3 | 0.66 | 0.96 | 0.78 |
| hardcoded_config_v3 (any literal URL/path/model/zone/port/limit) | 0.84 | 0.31 | 23% | 0.7 | 0.69 | 0.85 | 0.76 |

# Section 1: classification of all docket-49 functions (8f9a15e1)

5 Pick-one questions (role, layer, domain, data sensitivity, strongest effect) per function; 1,783 functions
in 316 files (incl. tests and build scripts), 20.9 s, $0.13, 0 errors. Output: run-06/CLASSES.json (local).
Application code (excluding prototype/build, tests, experiments, docs, tools): 490 functions.

| Question | Application-code distribution |
|---|---|
| Role | data access 107, transformation 90, business logic 53, AI call 42, utility 41, external call 35, configuration 34, rendering 32, validation 28, request handler 16 |
| Layer | domain 148, integration 90, storage 87, infrastructure 54, API 35, UI 14 |
| Domain | email 96, matters 62, general 61, AI platform 57, calendar 56, documents 55, assistant 25, observability 24, tasks/notes 22, navigation 15, intake 10 |
| Sensitivity | legal content 209, none 103, app data 103, personal 42, credentials 30 |
| Effect | writes local 152, none 147, reads 140, writes external 49 |

Spot checks: the 30 "credentials" functions are the Google OAuth, Keychain/API-key and provider-post paths as
expected. "Writes external" also counts sending content to AI providers, so it doubles as a data-leaves-the-
machine inventory; answers under ~0.5 confidence there are doubtful. 127 of 1,293 tooling-path functions were
not labelled tooling (mostly helpers inside scripts labelled by what they do).
