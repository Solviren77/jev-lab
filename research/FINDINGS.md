# What six Jev videos teach Jev Lab

Sources: six YouTube videos (transcripts in `transcripts/`, local only; per-video notes with timestamps in `notes/`). Auto-captions; vendor and creator numbers are unverified.

## How people actually use Jev

1. **Bulk, not one-off.** Every practical demo runs over hundreds to thousands of items: 50 support emails in 4.2 s for $0.026 (Simon Scrapes); 1,000 emails × 7 questions in 6 s for $0.09 (Nate Herk); 1,300 posts in 106 s for $0.04 and 227 call transcripts in 13 s for $0.07 (Ben AI).
2. **One item per call, all questions in that call, many calls at once.** Each item (email, file, row) is its own state; every question about it goes in the same request (1–100 questions; extra questions are nearly free); a worker pool runs 8+ calls concurrently. Nate's 70 s → 6 s came from parallelism.
3. **Mix all three types on the same item.** Yes/No for "should code act?", Pick one for "which pile?", Score for "how much / how urgent?". Pick-one always gets a `none`/`other` option.
4. **Definitions do the work.** Each Yes/No has a "counts as yes" definition; each option and each score level has a written description of what it is and isn't. Questions are atomic (no "or", no compound scores).
5. **Keep state small and named.** Only the fields the decision needs (e.g. from, subject, body). Large raw states hurt accuracy (ThePrimeagen's 20k-token game state). Limits: ~32k tokens for state + largest question, ~64k for state + all questions.
6. **Thresholds are action policy, tuned on labelled examples.** Per-question thresholds; low-confidence items go to a "needs review" pile. The confidence field measures spread, so top probability or the gap to the runner-up can be more useful (LangChain × TypeSafe).
7. **Jev filters, Claude writes.** Jev sorts cheaply; only the items it flags go to Claude for drafting, summarising or themes. Workflows are saved and run on a schedule.
8. **Results are read in aggregate.** Counts per category, score histograms, drill-down to the items, CSV export, time and cost per run.

## What Jev Lab must change

| Priority | Change | Why (source) |
|---|---|---|
| 1 | Add folders and many files at once; each file (or each email/row) is one item | All videos; Nate, Ben |
| 2 | Run a batch through a concurrent worker pool, one call per item with all questions | Simon, Nate, LangChain |
| 3 | Results table: one row per item, one column per question, sortable, filter, CSV export, totals and cost | Nate, Ben |
| 4 | Pick one always includes "Other"; every option and level has an optional description | Simon, LangChain, Nate |
| 5 | "Needs review" pile for answers under threshold or close calls | Simon, ZazenCodes, LangChain |
| 6 | Token meter and warning when a document is too large; split long documents | LangChain, Nate, ThePrimeagen |
| 7 | Saved recipes (questions) reusable on any folder, and scheduled/watched runs | Ben, Nate |
| 8 | Hand-off: export the flagged items for Claude | Ben, ZazenCodes |
| 9 | Labelled-sample check: mark ~20–100 items correct/wrong to see accuracy per question | Nate, LangChain |
| Later | Follow-up questions that depend on earlier answers (hierarchies) | ThePrimeagen, Simon |

## Treat with caution

Vendor speed/cost multiples (20–1000×), calibration and "doesn't hallucinate" claims, single unchecked demo runs, and creators promoting paid courses. Nate's 6 s batching used a modified backend whose details aren't shown; the videos do not show several items packed into one call.
