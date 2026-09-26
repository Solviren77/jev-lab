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

# Experiment 5: security and AI question sets, routed (docket-49 8f9a15e1)

Routed by section-1 classes: 390 of 490 application functions (security 373, AI 71); 4.8 s, $0.022.
Key: 3 independent Claude reviewers per function, majority vote (1.4M reviewer tokens).

| Set | Question | Key yes | Reviewers unanimous | Jev avg yes/no | Cutoff | Precision | Recall | Verdict |
|---|---|---|---|---|---|---|---|---|
| AI | prompt includes untrusted text | 35 | 94% | 0.87/0.25 | 0.6 | 0.94 | 0.97 | Trust |
| AI | model settings inline | 3 | 100% | 0.85/0.13 | 0.7 | 1.00 | 1.00 | Trust (small n) |
| Security | sends data out | 56 | 98% | 0.74/0.11 | 0.4 | 0.77 | 0.89 | Trust as inventory |
| AI | no size limit | 26 | 93% | 0.66/0.22 | 0.3 | 0.69 | 0.96 | Filter |
| Security | path from outside input | 10 | 99% | 0.72/0.19 | 0.7 | 0.58 | 0.70 | Filter |
| Security | string-built SQL/shell/HTML | 11 | 99% | 0.66/0.16 | 0.8 | 0.67 | 0.36 | Weak |
| AI | failure unhandled | 6 | 93% | 0.83/0.36 | 0.5 | 0.22 | 1.00 | Filter only (over-flags) |
| Security | data-changing request unguarded | 4 | 100% | 0.84/0.23 | 0.8 | 0.10 | 0.75 | Over-flags |
| AI | output unvalidated | 3 | 94% | 0.56/0.44 | – | 0.07 | 1.00 | Drop |
| Security | secret inline | 0 | 100% | –/0.05 | – | – | – | No cases (good) |
| Security | path checked (problem = No) | 2 no | 100% | – | – | – | – | Rephrase as problem |
| AI | untrusted separated (problem = No) | 2 no | 100% | – | – | – | – | Rephrase as problem |

The "yes = safe" questions default to yes when not applicable, so they can't be titrated this way; rephrase
as "uses outside path WITHOUT a check" / "puts untrusted text into instructions".

# Experiment 5b: real-world severity of the 3-reviewer findings

6 Claude reviewers traced callers, routes and upstream protections for the 67 majority-confirmed findings
(48 functions). Result: 28 real after whole-path review — 0 critical, 0 high, 2 medium, 23 low, 3 none.
- Not real: all string-built SQL/shell/HTML findings (parameterized SQL, argv subprocess, hash-derived names),
  all 4 "unguarded state change" handlers (protected by do_POST origin/host checks), path findings in do_GET/_file
  (containment checked in the caller), most "AI failure unhandled" (caught by route handlers).
- Real, medium: provider.codex / provider.run concatenate instructions and inbound email into one prompt in
  Codex mode (prompt-injection exposure; the Claude path separates them). One root cause.
- Real, low: no size cap on email/documents sent to models (draft_reply, email_issues, triage, mail_classify,
  matter_write, matter_chat, guarded_generation), inline model in client_update, triage.main writing message
  bodies under an unchecked path, allowlist hardening in _apply_register_change.
Lesson: function-level "yes" is accurate about the function but most findings are neutralised by context the
function can't show; path/taint context is the next lever.

# Experiment 6: taint pass + Sonnet review (docket-49 8f9a15e1)

Code-built call graph (name-matched), sources (5 HTTP entry points, 8 mail reads, 9 model-call functions),
reach chains, guards on the chain, callers' caught exceptions and sink facts, added to Jev's state with an
instruction to count a problem only if outside input reaches it unprotected. 390 calls, 5.2 s, $0.028.

Flags at 0.5, before → after: unguarded state change 67 → 4; path from input 65 → 24; string-built
SQL/shell/HTML 30 → 22; model failure unhandled 27 → 19; no size limit 28 → 30; output unvalidated 35 → 35;
model inline 5 → 5.

Sonnet (5 reviewers, read-only) on all 139 remaining flags: 31 real (18 medium, 12 low, 1 none).
Real by question: size limit 19/30, failure unhandled 4/19, model inline 3/5, output unvalidated 3/35,
state change 1/4, string-built 1/22, path 0/24. Graph facts judged correct in 95/139; wrong mostly where the
protection lives in a CALLEE (jev.ask's MAX_BYTES cap and probabilities() validation, provider.check schema
validation, _calendar_mutation's origin check), which a caller-only graph can't see.
Caveat: the Sonnet input included the earlier Opus-path verdict ("prior_truth") for 47 flags, so those
verdicts are not independent; Sonnet agreed on 40 and disagreed on 7 (mostly calling output "unvalidated"
where Opus found provider.check validation).

# Experiment 7: downstream protection facts (run-09)

Added per-function protections (validation that raises, size caps, error catching, host/origin, path
containment, escaping; pattern-matched) and the same protections found in functions each one calls
(strictly resolved callees, depth 3). 390 calls, 6.0 s, $0.030.

Flags at 0.5: 139 → 89 (57 dropped, 7 added; Sonnet judged all 7 added not real).
Of the 31 Sonnet-real flags, 13 were kept and 18 dropped: 16 of the 19 real "no size limit" findings were
suppressed because provider.claude/_post matched the size-cap pattern (length checks unrelated to the
input sent), a false protection. Validation/error facts worked: output-unvalidated 35 → 28 (3/3 real kept),
failure-unhandled 19 → 8 (3/4 kept), state change 4 → 0 (lost 1 low).
Hybrid (downstream facts for all questions except size limit): ~113 flags with 29 of 31 real kept.
Lesson: a wrong "protected" fact is worse than no fact — it hides real problems.

# Experiment 8: input-specific size-cap detector (run-10)

"Caps size" now requires a length check or slice on a value the same function then passes to a model or
transport call (error-text slices ignored). 8 functions qualify (jev.ask MAX_BYTES, assistant.turn,
provider.agent, matter_update.prepare, …); provider.claude/_post no longer do. 390 calls, 6.5 s, $0.029.

| Version | Flags at 0.5 | Sonnet-real kept |
|---|---|---|
| upstream facts only (run-08) | 139 | 31/31 |
| + downstream, loose size pattern (run-09) | 89 | 13/31 |
| + downstream, fixed size detector (run-10) | 95 | 20/31 |

Size-limit: 10 of 19 real kept (was 3). Of the 9 still dropped: 4 sit behind jev.ask's genuine 100 KB cap
(jev_templates, jev_topic_review, guarded_write) — arguably Sonnet's "real" was too strict; 2 sit behind
assistant.turn/provider.agent caps; mail_classify.propose was dropped because only its Jev branch is capped
(the graph is branch-blind); write_row, provider.run and guarded_generation fell to 0.36–0.48, just under 0.5.

# Experiment 9: branch-aware facts, corrected key, per-question cutoffs (run-11)

Facts now list model calls per direct callee with that path's protections (e.g. mail_classify.propose:
via propose → capped; via run → no cap). Key corrected: 4 size findings behind jev.ask's 100 KB cap are
not real. 390 calls, 6.1 s, $0.031.

At a flat 0.5: 104 flags, 20/27 real. Per-question cutoffs (chosen on this same data — needs a held-out
check): string-built 0.7, path 0.7, state change 0.5, output unvalidated 0.6, model inline 0.7, failure
unhandled 0.4, size limit 0.45 → 76 flags, 25/27 real. Sonnet reviewed the 7 unreviewed flags: 2 new real —
provider.agent sends the whole matter corpus plus accepted documents as context with no cap (medium; the
size detector credited agent for capping other content), fixed_tokens failure uncaught in the triage CLI
(low). Updated: 27 of 29 real in 76 flags, vs 139 flags in run-08.
"Path from outside input" has 0 real findings in docket-49 at any cutoff: keep only as an inventory.

# Experiment 10: nested calls — pattern 1 (localise → judge) and 5 (Jev picks, code fetches, Jev judges)

170 candidates (run-11 answers ≥ cutoff − 0.15); round A 293 calls, round B 129 calls, 6.6 s, $0.022.
v1 asked "which line shows the problem"; for absence problems Jev answered "none" (nothing to point at).
v2 anchors absence problems on a present line (the model call, the data write) — then localisation works.

On the 76 run-11 flags (27 real of 29):
| Filter | Flags | Real |
|---|---|---|
| none (run-11) | 76 | 27 |
| drop if round A picks "no line" | 56 | 25 |
| + confirm ≥ 0.3 | 47 | 22 |
| + confirm ≥ 0.5 | 29 | 14 |
Pattern 5 changed nothing: Jev mostly answered "none of these" when asked which caller/callee protects,
and where it named one, the fetched code rarely scored ≥ 0.7 as protecting. The confirm round drops real
and false flags at about the same rate, so it adds no discrimination beyond the "no line" step.
Per question after the "no line" step: path-from-input 13 → 5 (0 real), string-built 5 → 1 (lost the one
real, practice_context), size limit 20 → 15 (14 → 12 real), output-unvalidated 15 → 12 (3 real kept).
Bonus: every kept flag now carries a line number (accuracy of the line not yet checked).
