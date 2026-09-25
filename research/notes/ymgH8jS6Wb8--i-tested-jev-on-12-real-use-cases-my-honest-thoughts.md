# Notes: I Tested Jev on 12 Real Use Cases. My Honest Thoughts.

- Source: Nate Herk | AI Automation, https://www.youtube.com/watch?v=ymgH8jS6Wb8 (uploaded 2026-09-19, 16 min)
- Transcript: `research/transcripts/ymgH8jS6Wb8--i-tested-jev-on-12-real-use-cases-my-honest-thoughts.md` (auto-captions; "TypeSafety" [00:01:10] = TypeSafe, "null" [00:01:10] = Noul, "Soul" [00:13:01] = Sol).

## 1. Summary

Nate Herk, an AI-automation YouTuber, tests Jev across roughly a dozen use cases and compares it with GPT-5.6 Luna, Terra, Sol, Opus and Fable on speed and cost [00:00:00]. Most demos run in a self-built "playground" dashboard that applies a set of typed questions (yes/no, choice, score) to 1,000-item corpora of emails, YouTube comments, community posts, X posts, meeting transcripts and video clips [00:04:48]–[00:11:48]. He also shows two live builds: a Chrome extension that labels X posts in real time, and a paper-trading prototype that makes a decision every second [00:09:32], [00:14:09]. His framing: Jev decides but doesn't write, so it should triage at scale and hand off to a frontier LLM for writing and analysis [00:03:39], [00:15:19]. He also says to check it with evals before trusting it [00:11:48].

## 2. Use cases demonstrated

| # | Use case | State given | Questions (type, wording, options/levels) | Results reported |
|---|---|---|---|---|
| 0 | Support ticket (explainer slide) | One support ticket [00:01:10] | Urgent? (yes/no); Which team? (choice, e.g. technical/billing/support); How frustrated? (score) [00:01:10] | Urgent yes at 99%, team = technical, frustration 1 of 2 [00:01:10]. He later calls the score 0 to 10 [00:02:24], which is inconsistent. |
| 1 | Email classification | 1,000 emails [00:05:54] | 7 questions [00:05:54]: invoice/receipt (Noul), brand deal (Noul), scammer/phishing (Noul), email type (choice), urgency (score), sponsor fit (score), plus one unnamed [00:04:48]. Invoice wording asks whether the email is a receipt, invoice, payment confirmation or billing notice; "yes" is defined as a charge, payment, payout or failed payout, with a 50% threshold [00:07:05]. Email type options: notification, newsletter, billing, opportunity, each with a definition [00:07:05]. Sponsor fit levels run from "not a sponsorship inquiry" to "strong fit"; urgency levels run from "nothing needed" to "action needed", 5 levels [00:07:05]. | All 7 questions: Jev about 70 s / $0.09 unparallelized, Luna 5 min / $0.62 [00:05:54]. With parallel calls and larger payloads: 6 s / $0.09 [00:05:54]. Invoice question alone: 4 s / $0.05, 763 no and 237 yes [00:07:05]. Sponsor fit: 942 at level 1 and none at "strong fit"; urgency averaged 2.8/5 [00:07:05]. He sums it up as Luna costing 12x more and taking 46x longer [00:08:19]. |
| 2 | YouTube comments | About 1,000 comments [00:08:19] | Comment type, worth a reply, video idea, sentiment, question difficulty (mix of choice, Noul and score) [00:08:19] | 5 s / $0.05. Console showed about $0.85 total for nearly 20,000 requests [00:08:19]. |
| 3 | Community (Skool) posts | Posts [00:08:19] | Question type, needs help, needs team answer, churn risk, member experience level, testimonial strength [00:08:19] | No numbers given. |
| 4 | X feed (dashboard + Chrome extension) | X posts as they appear on screen [00:09:32] | On topic?, category, breaking news?, video-idea potential; extension labels posts breaking / golden nugget / AI slop [00:09:32] | Labels appear almost instantly; no accuracy figures [00:10:42]. |
| 5 | Meetings | Transcripts from Fireflies/Granola [00:10:42] | Call type, decisions made, action steps, next steps with owner and timeline, tension/frustration, waiting on Nate, revenue relevance [00:10:42]–[00:11:48] | Only qualitative: many calls lack clear next steps; little tension [00:10:42], [00:11:48]. |
| 6 | Video clips | Clips an LLM (Astra) cut from his videos [00:11:48] | Works standalone?, hook strength, clip type, needs screen?, has a quotable line? [00:11:48] | "A lot of them, no" on working standalone [00:11:48]. |
| 7-10 | Suggested only (not demoed) | Contracts, jobs/leads, brain-dump voice notes, customer support [00:13:01] | Contracts: risk type, clause type. Leads: red flags, lead quality, next steps. Brain dump: idea/task/journal, has a deadline, priority, life area. Support: routing, sentiment, urgency [00:13:01] | None. |
| 11 | Real-time paper trading | BTC price, updated every second [00:14:09] | Up / unclear / down (choice with confidence) [00:14:09] | Confidence scores shift every second and drive buys and sells. Trading fees cost more than Jev; about $2/day to run 24/7 versus much more for Sol, Opus and Fable [00:14:09]. He calls it poorly vetted; the X extension was "not doing very well in the first hour" [00:00:00]. |
| 12 | Browser use / games (others' demos) | n/a [00:14:09] | n/a | Jev can't type into the browser, so it has to hand off to another model [00:15:19]. |

## 3. How Jev is meant to be used

- **Output types.** There are three: Noul (yes/no with confidence), Choice (pick one, with confidence) and Score (a level on a scale). No text or reasoning comes out; results are returned as JSON [00:01:10], [00:02:24].
- **Question design.** Each question gets a name, the question wording, a definition of what counts as "yes", and a confidence threshold, e.g. 50% [00:07:05]. Every Choice option gets its own definition [00:07:05]. Score levels are written in order from lowest to highest [00:07:05]. The user supplies the decision criteria [00:01:10].
- **Analysis from structure.** Jev can't find themes, but a well-designed set of questions can be aggregated so the data "tell a story" [00:10:42].
- **Batching and parallelism.** Seven questions run over 1,000 items together [00:05:54]. Parallel calls with bigger payloads cut runtime from about 70 s to 6 s at the same cost [00:05:54].
- **Routing to an LLM.** Jev triages at scale, e.g. 5,000 comments, and a frontier model then writes replies or finds themes in the selected subset [00:03:39]. The browser case shows the same handoff [00:15:19].
- **When to use it.** Thousands of items, a corpus, classification in production, or real-time decisions [00:03:39]. Use ChatGPT-type models for small item counts, explanations, brainstorming or chat [00:03:39].
- **Evals first.** Build a golden set of 100 items with correct answers, then compare Jev against Opus and Sol on accuracy, cost and speed [00:11:48]–[00:13:01].
- **Automation pattern.** Classify each new post, comment, CRM entry or lead as it arrives and write the result to a database. He says cost matters more than speed here [00:09:32].
- **Limits.** 64k-token input context, versus about 1M for Claude/GPT [00:03:39]. Can't write, summarize, find themes or do deep analysis [00:02:24].
- **Claimed numbers.** 20-200x faster and 40-400x cheaper, output tokens free (attributed to Diogo) [00:02:24]. His email test: 1,000 emails x 7 questions in 6 s for $0.09 [00:05:54]. Trading: about $2/day at one decision per second [00:14:09].
- The video doesn't cover hierarchies or nested questions.

## 4. Tools and interfaces shown

- **Playground dashboard** (built by Nate). Tabs per dataset (emails, comments, Skool, X feed, meetings, clips) [00:04:48], [00:08:19]. It has a question list with add/edit and "redo everything" + run, and a model switcher (Jev vs Luna) [00:04:48]–[00:05:54]. Results show per-question counts (yes/no totals, level histograms, averages) plus time and cost for each run [00:07:05].
- **Question editor.** Fields for name, question, what counts as yes, and threshold; per-option definitions for Choice; ordered levels for Score [00:07:05].
- **Jev console.** Shows usage in dollars and request count [00:08:19].
- **Chrome extension "Jev Judged".** Overlays labels on X posts [00:09:32].
- **Paper-trading UI.** Live confidence per second, trade log, and a daily cost comparison between models [00:14:09].
- **Access.** Waitlist at TypeSafe AI, plus the Vercel AI Gateway and OpenRouter [00:01:10]. The SDK, compile tool, spreadsheets and harnesses aren't shown.

## 5. Implications for Jev Lab

1. **Bulk and folder input is the core use case.** Every demo runs on about 1,000 items [00:05:54], [00:08:19]. This supports adding folders and multi-select, and treating a folder as a dataset of items.
2. **Batch and parallelize.** Moving from one call per document to parallel calls with larger payloads was the 70 s to 6 s change [00:05:54]. Send many items per call and several calls at once, all questions per item, with a concurrency setting.
3. **Question editor with the fields Nate used.** Name, wording, "counts as yes" definition and a threshold slider for Noul; per-option definitions for Choice; ordered level descriptions for Score [00:07:05].
4. **Aggregate results view.** Yes/no counts, per-option counts, level histograms and averages, with filtering or drill-down to the items behind each bar [00:07:05]. This is how Jev output "tells a story" [00:10:42].
5. **Show time and cost for each run,** plus a running total [00:05:54], [00:08:19].
6. **Incremental background runs.** Classify only new or changed files in watched folders and store results persistently. This matches his database-per-new-item pattern [00:09:32].
7. **Golden-set evals.** Let the user label about 100 items and score Jev's accuracy per question [00:11:48]. An optional comparison against Claude would help too.
8. **Handoff export.** Filter items, e.g. "needs reply = yes", then export them or send them to Claude for writing and themes [00:03:39].
9. **Context guard.** Warn about or chunk documents that exceed the 64k-token input limit [00:03:39].
10. **Question templates** for his domains: email, comments, meetings, contracts, leads, brain dump, support [00:13:01].

## 6. Claims to treat with caution

- The 20-200x speed and 40-400x cost figures come from the founder's announcement and aren't independently verified [00:02:24].
- Speed/cost comparisons come from his own quick tests; he says one run doesn't prove general ordering [00:02:24]. No accuracy was measured against Luna.
- The 6-second result comes from his own modified backend; the batching details aren't shown [00:05:54].
- He reports no accuracy figures for any use case. His eval advice isn't applied in the video [00:11:48].
- The claim that Diogo "co-invented ChatGPT" is promotional and unverified [00:00:00].
- The trading demo is by his own account poorly vetted, and fees exceed the decision cost. It isn't evidence of profitability [00:14:09].
- The X extension was performing poorly early on [00:00:00].
- Support-ticket score scale is described inconsistently (1 of 2 vs 0-10) [00:01:10], [00:02:24].
- The video includes sponsor/SOP promotion [00:04:48], and the opening claim that it will change automations is his opinion [00:00:00].
