# Notes: Every Jev Concept Explained in 37 Minutes

Source: Simon Scrapes (YouTube, D-Z5HnLW_ho, uploaded 2026-09-23, 37 min). Auto-captions render "Claude Code" as "claw code", "TypeSafe" as "type safe"/"type face", Jev as "Jeff"/"Jeb", and "route" as "root".

## 1. Summary

Simon Scrapes walks through TypeSafe's docs for Jev, which he calls a "judgment" or "System One" model. It turns messy inputs (state) into calibrated numbers for typed questions and never writes text [00:01:19]–[00:02:35]. He explains the three question types (Noul, Choice, Score), the confidence value, and how Jev works alongside Claude rather than replacing it [00:05:08]–[00:12:34]. He then installs the TypeSafe skill in Claude Code and builds a triage of 50 support emails into four piles, which took 4.2 seconds and cost about $0.026 [00:13:53], [00:30:33]. He finishes with four patterns from the docs: speculative fan-out, confidence-gated routing, weighted scoring and intent routing [00:31:48]–[00:35:45].

## 2. Use cases demonstrated

- **Order fraud check (conceptual).** State: one order email. Noul questions such as "billing/delivery address mismatch?" The code flags the order only when every answer clears a threshold, for example 0.95 [00:00:00]–[00:02:35]. No results are shown.
- **Angry customer email (conceptual, one request with three types)** [00:06:26]–[00:11:19]:
  - Noul "does this customer sound angry?" returned 0.9, which is above the 0.8 escalation threshold; a result below 0.2 would be deprioritized.
  - Choice "which team?" over billing/technical/sales returned 0.85/0.10/0.05 with high confidence, so the email goes to billing.
  - Score calm/annoyed/furious returned 2.4 of 3, meaning "annoyed, edging toward furious", and is used to rank the inbox worst first. In the combined example, 2.4 came with 0.8 confidence on a four-level scale [00:11:19].
- **Browser agent (Google Flights, voice Chrome; others' work).** Every page element is numbered. Two Choices are asked at once: the action (click/type/scroll) and the element number. Confidence acts as a safety catch: when it is low, the agent asks the user [00:07:42]–[00:08:53], [00:33:04]. Reported as about 7 seconds per fill [00:00:00].
- **Website sessions (others' work).** A Noul per event (rage click, dead click, error) plus a Score for how bad the whole session was, sorted worst first so a human opens only the top 10 [00:10:03]. Reported as 3M sessions in 40 seconds for about $2 [00:00:00].
- **Lead scoring (others' work).** 700 leads in 40 seconds for about $0.09 [00:13:53].
- **Guardrails and citations (TypeSafe docs).** Jev screens input to Claude for jailbreaks or harm and screens Claude's output. In the citation example, 8 citations were checked against the source: 4 fine, 1 non-existent, 1 saying the opposite, 2 routed to a person as unsure [00:12:34].
- **Key test (live).** State: "charged twice, please fix ASAP". Noul "customer is reporting a billing problem" with descriptive true/false criteria. Result: 0.99, 324 input and 24 output tokens, about 0.3 seconds, a cost of about $0.0000136 (roughly 73,000 calls per dollar) [00:16:14].
- **Support triage (live, 50 emails in a CSV)** [00:18:41]–[00:31:48]:
  - State: one structured object per email, holding email fields plus customer facts (plan, customer-since) and leaving out thread history [00:23:25]–[00:24:41].
  - Five questions in one request [00:24:41]–[00:28:13]:
    - Choice for topic: billing/technical/feature request/account/none, each defined by what it is and is not.
    - Noul for refund request: cancelling without asking for money back counts as false.
    - Score for breakage: none/cosmetic/annoying (degraded, with a workaround)/cannot use.
    - Score for anger: calm/annoyed/furious.
    - Choice for judgment needed: standard/judgment/unusual.
  - Second pass on Claude's drafts: two Nouls, "answers the question?" and "promises refund/discount?". Only drafts that pass both are kept [00:22:13].
  - Routing rules: money questions go to a person under a high threshold; low category confidence or an unusual case goes to a person; broken product goes to engineering; feature requests are logged; everything else is drafted by Claude. Each rule has a threshold [00:21:05]–[00:22:13], [00:28:13].
  - Results: 4.2 seconds with 8 concurrent workers (31 seconds sequentially), $0.026 total. Priority weighting was 70% anger and 30% severity. 19 emails went to a person and 19 to Claude replies; the rest went to engineering or the feature log [00:30:33]–[00:31:48].
- **Smart home (TypeSafe docs demo).** One request asks the request kind, rooms, device and action. Compound commands go to an LLM to be split and then judged again; general questions go to an LLM [00:35:45].

## 3. How Jev is meant to be used

- Jev returns only a number or one of the options you define, so it cannot invent an answer. That is a strength and also a constraint [00:02:35]–[00:03:55]. Its probabilities are claimed to be calibrated like a weather forecast [00:03:55].
- Your code acts on the numbers with ordinary if-statements. Jev never escalates anything itself [00:06:26].
- Pick the type by what the code does next: act or don't act means Noul, route means Choice, sort or rank means Score [00:11:04]–[00:11:19]. Choice and Score return confidence, which comes from how spread out the probabilities are; Noul does not [00:07:42], [00:10:03]. A Score can land between levels, for example 2.4 [00:08:53].
- Always include a "none" option in a Choice so the model has an out [00:21:05], [00:25:56].
- Criteria should be descriptive, saying what each option is and is not, with examples [00:16:14], [00:25:56]–[00:27:02].
- State should be named fields in one object per item, not a flat string, with irrelevant text left out. The hard limit is 64k tokens per request, and a request should be nowhere near it [00:23:25]–[00:24:41].
- Start from the action, not from the data. The checklist [00:29:02]–[00:30:33]:
  1. List the actions.
  2. Write each trigger as a sentence; that sentence becomes the question and implies its type.
  3. Define what a person would look at, which is the state.
  4. Add edge cases.
  5. Set each threshold by what a wrong answer costs.
- Batch questions: send all of them in one request. They run in parallel, the text is read once, and extra questions are "almost free". Include speculative questions that may not apply; this is called speculative fan-out [00:24:41]–[00:25:56], [00:31:48]–[00:33:04].
- Items are sent one request each, with concurrent workers (8 in the demo). The video does not show many items packed into one call [00:30:33].
- Confidence gating: set one threshold per action according to the cost of being wrong. The voice-banking example uses 0.6 for a balance check and about 0.85–0.95 for a transfer [00:33:04].
- Weighted scoring: split a vague judgment (for example "good candidate 1–10") into independent dimensions and weight them in code, with weights varying by role [00:33:04]–[00:34:22].
- Intent routing: Jev classifies each request and routes it to deterministic code, an LLM or a human; low-confidence requests go to a human [00:34:22]–[00:35:45]. This works like a hierarchy, for example a complaint gets a follow-up complexity question.
- Claude's role: Claude handles reasoning, specialist knowledge and writing. Jev acts as a guard before or after Claude and does bulk work in Claude's place, so Claude only gets the unsure rows [00:12:34]–[00:13:53]. The founder described Claude as the conversation and Jev as the plumbing [00:05:08].
- Cost and speed: TypeSafe claims 40–1000x cheaper and 20–400x faster than LLMs, at about $0.04 per million input tokens with output practically free [00:02:35]. It is also claimed to be more consistent across runs than chat models [00:03:55].

## 4. Tools and interfaces shown

- **TypeSafe skill for Claude Code:** two terminal commands add a marketplace and plugin, shown via /plugins. The skill must be named in the prompt ("use the TypeSafe skill") [00:13:53]–[00:15:02]. It is a rulebook and does not run anything itself: it covers question types, wording, batching and where thresholds live [00:17:31].
- **Console at typesafe.ai:** creates API keys, stored in .env as the TypeSafe API key; also offers a copyable agent prompt. The skill docs are at docs.typesafe.ai/agent-skill [00:13:53]–[00:15:02].
- **Claude Desktop:** you can upload the skill's markdown file under Customize > Skills. He had not tested this himself [00:15:02].
- **Model id "jev latest":** shown in the request JSON as state, questions and criteria [00:16:14].
- **OpenRouter:** Jev is also available there directly, but then you write the questions and criteria yourself [00:17:31].
- **Workflow:** a CSV or Google Sheet as input (an email MCP is possible), a questions.py plan file with state, questions and routing, Claude-written routing scripts, and a Markdown results report [00:18:41], [00:23:25], [00:28:13], [00:30:33].
- **Free checklist:** his own, offered via his community (lead magnet) [00:28:13].

## 5. Implications for Jev Lab

- **Batch input:** add folders or many files as one run and process them with a bounded concurrent worker pool, which directly fixes the one-document-per-call weakness. The demo used 8 workers and got about 7x the sequential speed [00:30:33].
- **Many questions per call:** always send every question in one request per item, and nudge users to add speculative questions because they cost almost nothing [00:24:41], [00:31:48].
- **Action-first setup wizard:** have users define piles or actions first, then write each trigger sentence, then pick the type. Suggest the type automatically: act means Noul, route means Choice, rank means Score [00:29:02]–[00:30:33].
- **Question editor safeguards:** require descriptive per-option criteria, meaning what it is and is not. Auto-add "None of these" to Choices. Show a Score level's description beside it [00:21:05], [00:25:56]–[00:27:02].
- **State builder:** map file metadata and CSV columns to named fields, with extracted text as one field. Warn when the state is large (64k hard cap) and let users exclude noise [00:23:25]–[00:24:41].
- **Routing rules as no-code if-statements:** per-rule thresholds, with low-confidence results going to a "Needs review" pile. Results appear as piles, not raw numbers [00:28:13], [00:33:04].
- **Weighted priority:** combine several Scores with user-set weights (for example 70/30) and sort each pile worst first [00:30:33], [00:33:04].
- **Multi-pass or conditional questions:** a second question set that runs only on some items, either follow-ups like complaint complexity or checks on generated text [00:22:13], [00:35:45].
- **Cost and time readout per run:** tokens, seconds and dollars, like the demo [00:16:14], [00:30:33].
- **CSV input:** support a CSV where each row is one item, alongside documents [00:18:41].
- **Optional Claude hand-off:** send uncertain items or ones that need writing to an LLM [00:13:53].

## 6. Claims to treat with caution

- The first-week showcase results (Flights in 7 seconds, 3M sessions for $2, 700 leads for $0.09) were built by others, cited from social media and not reproduced here [00:00:00], [00:13:53].
- The 40–1000x cost and 20–400x speed figures, calibration, and consistency across runs come from vendor claims. The presenter did not verify them independently [00:02:35]–[00:03:55].
- The founder's background (credited with the methods behind ChatGPT) is garbled in the captions and unverified [00:01:19].
- The 0.3 second latency is his own estimate [00:16:14]. The live-run figures come from one run of 50 emails, and nobody checked whether the piles were accurate [00:30:33].
- The video mixes up level counts: anger is described as three levels but also "scale of four" and "0 to three" [00:11:19], [00:31:48].
- The Claude Desktop skill path was untested [00:15:02].
- The checklist is his own synthesis, not TypeSafe guidance, and it promotes his community [00:28:13]–[00:29:23]. Parts of the video are promotional, including a subscribe ask [00:11:19] and the channel's affiliate links.
