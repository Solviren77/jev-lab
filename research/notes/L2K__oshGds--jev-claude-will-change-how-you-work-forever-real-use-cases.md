# Notes: Jev + Claude Will Change How You Work Forever (Real Use Cases)

Source: Ben AI (Ben van Sprundel), https://www.youtube.com/watch?v=L2K__oshGds, uploaded 2026-09-23, ~10 min. Auto-captions render "Jev" as "Jeff" and "Claude" as "Cloud"/"cloth"/"claw"; corrected below.

## 1. Summary
Ben, a creator who sells an AI accelerator and agency services, presents Jev as a decision-only model and shows six examples of using it from Claude (mostly Claude Code) [00:00:00] [00:04:11]. He describes Jev as outputting only predefined decisions (yes/no or multiple choice), not text or reasoning [00:00:00] [00:01:24]. The demos are bulk classification or scoring jobs (YouTube comments, leads, churn risk, community posts, support calls, a browser agent), each reported with item count, time and cost [00:02:44]-[00:10:00]. He never shows raw Jev calls or question schemas; Claude builds the calls from the API key plus the docs page [00:01:24] [00:02:44]. Typed question names (Noul/Choice/Score) are not named explicitly; only yes/no ("null", likely "Noul") and multiple choice are mentioned [00:01:24].

## 2. Use cases demonstrated
| # | State given | Question(s) (type, wording, options) | Results reported |
|---|---|---|---|
| 1 | Every comment on his YouTube channel over the last year [00:02:44] | Choice: sort each comment into positive, negative, constructive feedback, unanswered question, answered question; instruction "use Jev only", output CSV + dashboard [00:02:44] | Jev run figures not stated in captions. Comparison run with Claude Opus 5: skipped some comments, 1,400 analysed, 34 min, $23 [00:02:44]. Reliability claimed "almost similar" to Opus, better than Sonnet [00:02:44] |
| 2 | List of 250 potential leads [00:02:44] | Two criteria: is the person a decision maker; are they US-based (implicitly yes/no), combined into a user-specified scoring system [00:02:44] | 250 leads in 4 s for $0.01, scores in Excel [00:02:44]. Packaged as a reusable "score leads with Jev" skill [00:04:11] |
| 3 | Activity data for 203 new community members from the last month: days since joining, posts, last login, comments, meetings joined [00:05:34] | Score: churn risk 1-10 (1 lowest, 10 highest) [00:05:34] | 25 s, $0.01, Google Sheet colour-coded by score; wrapped in a skill scheduled every two weeks [00:05:34] |
| 4 | All community posts over the last year [00:07:02] | Choice: community feedback, technical question, sales question, business question, intro, win (he says "six buckets") [00:07:02] | 1,300+ posts, 106 s, $0.04, dashboard; routing idea: technical question to CTO [00:07:02] |
| 5 | 227 customer support call transcripts [00:07:02] | Choice: one of six buckets (labels not stated) [00:07:02] | 13 s, $0.07, Claude-built dashboard [00:07:02] |
| 6 | Browser agent screens while scrolling his YouTube feed (AI tab) for 5 min, via "Jev Ultrafast" browser-use repo [00:07:02] [00:08:28] | Yes/no per screen/video: is this a video about Claude? If yes, extract title and link to a Google Sheet [00:08:28] | 443 videos seen, 99 saved, $0.01; sheet includes probability; a 55-score item at the bottom was not actually about Claude [00:08:28] [00:10:00]. Repo demo also books Zurich-London flight in 7 s [00:08:28] |

## 3. How Jev is meant to be used
- Output is decisions only, defined in advance; model classifies into one of them [00:00:00] [00:01:24].
- Good for classification and routing, especially large datasets [00:01:24]. Not for written text, maths/counting, media output, or complex reasoning tasks [00:01:24].
- Inputs can be the same as for an LLM [00:00:00].
- Question design is delegated to Claude: he says which type to use is unimportant because Claude sets it up [00:01:24].
- Setup pattern: give Claude the API key and the Jev docs URL, then describe the task [00:01:24].
- Combine with an LLM: Jev scores/filters a large list cheaply; Claude does research or outreach only on the qualified ones [00:04:11].
- Package repeatable workflows as a Claude skill; schedule recurring runs (every two weeks) [00:04:11] [00:05:34].
- Real-time routing of new tickets/posts as they arrive is possible because of speed [00:07:02].
- Probability output is usable as a confidence signal; low-probability items (e.g. 55) were wrong [00:08:28] [00:10:00]. No explicit threshold rule stated.
- Cost/speed: claimed 20-200x faster, 40-400x cheaper, free output tokens [00:00:00]; $5 free credit on signup [00:01:24]. Observed: 250 items/4 s/$0.01; 203/25 s/$0.01; 1,300/106 s/$0.04; 227 transcripts/13 s/$0.07 [00:02:44]-[00:07:02].
- Batching, many-items-per-call, hierarchies and state design are not discussed; call structure is hidden behind Claude.
- Other ideas mentioned from third parties: real-time website headline adaptation per visitor type, routing tasks to the right LLM [00:10:00].

## 4. Tools/interfaces shown
- typesafe.ai sign-in and API key generation [00:01:24].
- docs.typesafe.ai handed to Claude as context [00:01:24].
- Claude / Claude Code as the interface: natural-language task, Claude writes the Jev calls and produces CSV, Excel, Google Sheets and dashboards [00:02:44] [00:05:34] [00:07:02].
- Claude skills and scheduled tasks [00:04:11] [00:05:34].
- Jev Ultrafast (browser-use GitHub repo), used via Claude Code [00:07:02] [00:08:28].
- No playground, SDK code, compile tool or harness is shown on screen per the captions.

## 5. Implications for Jev Lab
- Bulk is the core use: every demo runs over hundreds to thousands of items [00:02:44]-[00:08:28]. Folder/multi-file import and batched runs are the top priority; one-document-per-call does not match the demonstrated workload.
- Tabular input (rows as items, columns as state, e.g. churn activity fields) should be supported alongside documents [00:05:34].
- Results views should be table + dashboard: counts per category, colour-coded scores, CSV/Excel export [00:02:44] [00:05:34] [00:07:02].
- Show the probability per item and sort/flag low-confidence results for review [00:08:28] [00:10:00].
- Question templates for common jobs: sentiment/feedback buckets, lead qualification (yes/no criteria to score), 1-10 risk score, ticket routing [00:02:44]-[00:07:02].
- Saved, reusable "recipes" and scheduled background runs (e.g. every two weeks over a folder) mirror the skill + schedule pattern [00:04:11] [00:05:34].
- Show time and cost per run, since those are the headline benefits [00:02:44].
- Optional hand-off step: export only items matching a category (e.g. qualified) for follow-up in Claude [00:04:11].
- Routing rules (category to person/folder) as a follow-on action [00:07:02].
- Help users design questions, since the video assumes an LLM does it for them [00:01:24].

## 6. Claims to treat with caution
- "20-200x faster, 40-400x cheaper", "free output tokens", and "I can confirm" from his own tests; no method shown [00:00:00].
- "Co-inventor of ChatGPT" provenance claim [00:00:00].
- Reliability "almost similar to Opus", better than Sonnet: no evaluation shown [00:02:44].
- Opus comparison ($23, 34 min) is a single run of an agentic workflow, not a like-for-like model comparison [00:02:44].
- Jev run figures for use case 1 are not stated in captions.
- Browser agent results were not shown live, by his own admission [00:08:28].
- "Will fundamentally change" and "gamechanger" framing; video promotes his paid accelerator [00:00:00] [00:04:11] [00:10:00].
- Third-party use cases mentioned without evidence [00:10:00].
