# Notes: Understand Jev (the only video you need)

- Source: ZazenCodes, https://www.youtube.com/watch?v=EAh1h1GYxDM (uploaded 2026-09-22, ~20 min)
- Transcript: `research/transcripts/EAh1h1GYxDM--understand-jev-the-only-video-you-need.md` (auto-captions; "Jeb", "Jeff", "Jab" = Jev; "new"/"Noul" = Noul; "Typescape" = TypeSafe)

## 1. Summary

The ZazenCodes presenter explains Jev as a TypeSafe decision model ("smart if statements") that is fast and non-generative. He also calls it a "System One" model, set against text-generating System 2 LLMs such as Claude or OpenAI models [00:00:00]–[00:01:27]. He covers the three primitives, Noul (true/false), Choice (pick one option) and Score (ordered scale) [00:02:55]. He demonstrates each one in a Python Jupyter notebook using the TypeSafe SDK [00:04:19]–[00:08:52]. He then asks several questions about one ticket in a single call [00:10:28] and builds a mock triage loop that routes tickets on confidence thresholds [00:12:01]–[00:14:56]. He closes by comparing Jev with classical ML and noting its limits [00:16:18]–[00:19:09]. Part of the video promotes his paid Skool course [00:12:01], [00:14:56].

## 2. Use cases demonstrated

| # | State | Question(s) | Result reported |
|---|---|---|---|
| 1 | "Click right here now to claim your Amazon gift card" [00:04:19] | Noul `is_spam`: is this spam or phishing? [00:04:19]–[00:05:46] | Probability 98% spam [00:05:46] |
| 2 | Login page keeps throwing an error (later 403) [00:05:46]–[00:07:24] | Choice "department": Billing (invoices, payments, subscriptions), Tech Support (login, error codes, bugs), Sales (pricing); instruction "which team should handle this ticket" [00:05:46]–[00:07:24] | Tech support at 100% confidence; the full distribution is a dict (billing 0%, sales 0%) [00:07:24] |
| 3 | "Critical alert: all payment webhooks are failing" [00:08:52] | Score "urgency": low / medium / high / critical [00:08:52] | Score 3 (0-indexed), with a legend that maps it to "critical". The presenter first misread it as 3/3 and says a 1-based display is clearer [00:08:52] |
| 4 | "Charged twice for an invoice on my credit card" [00:10:28] | Several at once: department (Choice), urgency (Score), jailbreak/prompt-injection risk (Noul), auto-refund eligible (Noul) [00:10:28] | Billing department, an urgency score, adversarial risk 2%, eligible for auto-refund [00:10:28]–[00:12:01] |
| 5 | Batch of support messages, each fed in as state [00:12:01] | Same question set as #4 [00:12:01] | Routed actions from real Jev calls. The downstream actions are mocked [00:12:01], [00:14:56] |

## 3. How Jev is meant to be used

- **Call shape:** `client.system_one(state, questions)`. The response includes the model name, usage (input/output tokens) and typed answers [00:05:46].
- **Billing:** only input tokens are billed, not output tokens [00:05:46]. The video gives no prices or latency figures, only "instant" [00:07:24], [00:10:28].
- **Schema guarantee:** answers always conform to the supplied schema. This is what "doesn't hallucinate" means here [00:01:27].
- **Question design:** Choice options carry descriptions ("criteria") plus an instruction [00:05:46]–[00:07:24]. Score levels are ordinal, and the answer comes back as a 0-based index plus a legend. Show it with the label or as 1-based [00:08:52], [00:10:28].
- **Multiple questions per call:** mixed types on one state are evaluated in parallel in a single request [00:10:28].
- **Many items:** shown as a loop of one call per ticket, not as many items in one call [00:12:01]–[00:13:26].
- **Confidence routing:** a switch-like cascade [00:13:26]:
  1. If prompt injection or adversarial, drop the item.
  2. If refund-eligible with confidence ≥ 0.85 and the department is billing, trigger an automated refund.
  3. If urgency is high but department confidence is low, escalate to a human or a Claude reasoning agent.
  4. Otherwise, take the default route.
- **Combining with an LLM:** Jev routes and decides; System 2 LLMs handle hard reasoning and text generation [00:01:27], [00:13:26].
- **Scale:** Jev is pitched as affordable for data too large to run an LLM over [00:10:28].
- **Limits:**
  - Jev has no niche or recent domain knowledge and does no web search [00:19:09].
  - Calibration of the probabilities is unproven [00:19:09].
  - It can do less than System 2 models [00:14:56].
  - It works out of the box with no training data. TypeSafe reportedly has ways to specialize or adapt it [00:17:42]–[00:19:09].
- **Hierarchies:** not covered.

## 4. Tools and interfaces shown

- **Python SDK (TypeSafe SDK package):** installed with `uv sync`, API key read from a `.env` file, a client object, and the primitive classes Noul, Choice and Score [00:04:19].
- **Jupyter notebook demo:** source is linked in the description (zazencodes-season-3 repo) [00:04:19].
- **Mock triage loop:** a Python script generated with Claude Code [00:12:01], [00:13:26].
- **Mind map:** used for the explanation [00:03:00 approx, in the 00:02:55 block].
- **Also mentioned:** Pi coding-agent harness extensions [00:12:01], a planned Pi extension [00:14:56], and a TypeSafe talk at the AI Engineer conference [00:01:27].
- **Not shown:** playground, compile tool or spreadsheet integrations.

## 5. Implications for Jev Lab

- **Multiple questions per document:** let users attach several questions of mixed types to each document and send them as one call per document [00:10:28].
- **Batch runner for folders:** run many files with one call each, with concurrency and progress. The loop pattern maps directly onto this [00:12:01].
- **Option descriptions in the question builder:** give each Choice option a description field, and give each question an instruction [00:05:46]–[00:07:24].
- **Score display:** always show the level label from the legend, never the raw 0-based index. The presenter misread this himself [00:08:52].
- **Show the full probability distribution** for each Choice, not just the top pick [00:07:24].
- **Routing rules with no code:** "if question X ≥ threshold and Y = option, put the result in category/folder Z". Include "needs review" buckets for low confidence and high urgency [00:13:26].
- **Adversarial screening:** a built-in prompt-injection Noul as a pre-filter, especially for untrusted documents in folders [00:10:28], [00:13:26].
- **Cost display:** show input-token usage per run, since only input is billed [00:05:46].
- **Hand-off to Claude:** an "Escalate to Claude" action for low-confidence items [00:13:26].
- **Set expectations in the UI:** warn that probabilities may not be calibrated and that Jev lacks niche or recent knowledge [00:19:09].

## 6. Claims to treat with caution

- "Doesn't hallucinate": the only guarantee is schema validity, not that answers are correct [00:01:27].
- The "petabyte-scale" affordability claim has no cost numbers behind it [00:10:28].
- "Trained on fully synthetic data" and "probably a transformer" are hearsay or guesses [00:17:42].
- The description of TypeSafe's RL-for-calibration training comes secondhand from the founder's talk. The presenter himself questions whether the probabilities can be trusted [00:02:55], [00:19:09].
- The founder name and background ("Dio Almida", ex-OpenAI 2024) come from auto-captions and are unverified [00:00:00].
- The 100% and 98% confidences come from single trivial examples [00:05:46], [00:07:24].
- The triage actions are mocked [00:12:01].
- The presenter says much of the Jev content on X is fake marketing. His own video promotes a paid course [00:14:56].
