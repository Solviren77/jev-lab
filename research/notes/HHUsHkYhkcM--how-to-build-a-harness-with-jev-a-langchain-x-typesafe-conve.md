# Notes: How To Build A Harness With Jev (LangChain x TypeSafe)

Source: https://www.youtube.com/watch?v=HHUsHkYhkcM (LangChain channel, uploaded 2026-09-22, 48 min). Transcript is from auto-captions; "Noul" appears as "new"/"renewal", LangSmith as "Langmith/Linksmith".

## 1. Summary

Sydney Runkle (LangChain OSS product manager) hosts Allie Laabs (TypeSafe developer relations) and Hunter Lovell (LangChain OSS technical lead) [00:02:06]. Allie describes Jev as an API-only "System One" model: no text output, fast decisions on well-scoped questions with typed schemas [00:02:06][00:03:42]. She walks through the three question types (Choice, Score, Noul) using a support-ticket example [00:12:06]–[00:16:42]. Hunter demos two LangChain middleware uses: blocking risky tool calls ("auto mode") and routing requests between a fast and a deep model, with LangSmith tracing [00:19:52]–[00:24:35]. The Q&A covers context limits, production use cases, confidence thresholds and large-state degradation [00:30:40]–[00:46:01].

## 2. Use cases demonstrated or described

- **Support ticket triage (slide example)** [00:12:06]–[00:16:42]
  - State: a customer message saying they have been trying to connect a Stripe account for 3 days [00:12:06].
  - Choice: which team should handle it, with options billing / technical / sales [00:12:06].
  - Score: how frustrated the customer appears, levels 0–2: calm / frustrated / very angry [00:13:39].
  - Noul: whether the message conveys urgency or time sensitivity [00:15:16].
  - Results: no numbers were shown. Choice returns probabilities per option. Score returns a value from 0 to n, and fractional values like 1.5 are possible. Noul returns P(yes) from 0 to 1 [00:12:06][00:15:16][00:16:42].
- **Tool-call safety classification ("auto mode" middleware)** [00:19:52]–[00:22:56]
  - State: the pending tool call. Tools were "update CRM / add internal note" and "delete customer account" [00:19:52].
  - Question: whether the action is dangerous, judged against true/false criteria written in the middleware instructions [00:21:18].
  - Results: adding a note to customer C123 was allowed and returned success. Deleting a customer with "no confirmation" was classified as risky, blocked, and returned status error [00:21:18][00:22:56].
- **Model routing middleware** [00:22:56]–[00:26:13]
  - State: the initial user query plus descriptions of the available models [00:24:35].
  - Choice: fast versus in-depth route [00:22:56].
  - Results: a simple rewrite request was routed "fast" to the cheaper model ("Luna"). A harder task was routed to the slower model ("Sol"). The decision is visible in the LangSmith trace [00:24:35].
- **Real-time chat filtering (described, not demoed)** [00:34:04]
  - State: each message in a high-volume Twitch chat.
  - Questions: a Score for quality or productiveness, which drives a user filter slider, plus parallel Choice questions (question / statement / hype) [00:34:04][00:35:28].
  - Results: about 100–150 ms per message and "won't break the bank" (claimed) [00:34:04].
- **Doom game agent (TypeSafe launch demo)** [00:35:28][00:41:42]
  - Choice: which monster or item to look at, asked every frame. It takes the top choice even when confidence is low, and a "stickiness" decay is suggested [00:41:42].
  - State tuning: an overly granular recent-actions array reduced accuracy [00:46:01].
- **GitHub issue labelling (Sydney, anecdotal)**: she found the probabilities and confidences confusing and had to calibrate [00:43:01].
- **Other mentions**: email spam/promo classification and department routing [00:03:42], progressive disclosure, tool selection, RLMs and code mode for coding agents [00:32:23], Jev-as-a-judge in LangSmith evals (video description only), and a "Jevify" skill that scans code for LLM decisions that could be swapped to Jev [00:27:44][00:29:15].

## 3. How Jev is meant to be used

- **Scope**: use it for questions a panel of smart humans could answer in about 5 seconds. It is not for multi-step reasoning [00:05:25]. Your code composes many System One decisions into a reasoned output [00:07:06].
- **Not an LLM drop-in**: it sits at decision points inside the harness, not as the agent's main model [00:18:16]. LLMs remain for generating prose [00:10:28].
- **Call shape**: one state plus an array of questions, from 1 to 100, answered in a single call [00:12:06]. Parallel questions per message are cheap [00:34:04].
- **Question design**:
  - Break each question down until it can't be broken down further. Avoid compound questions [00:13:39].
  - Use one axis per Score, and use two Scores when there are two axes [00:13:39].
  - Define every Score level semantically so scores are comparable across many documents [00:13:39][00:15:16].
  - An "or" inside a Noul is a yellow flag [00:15:16].
  - Choice works best with one dominant answer and options that don't overlap [00:12:06].
- **State design**:
  - Include only what the decision needs. Very large states can reduce accuracy (see the "model jaggedness" docs page) [00:44:33].
  - When you have to send a large unstructured text, iterate on the questions and test [00:44:33].
  - Trimming the state also saves cost, though cost is usually small [00:44:33].
- **Limits**:
  - The state plus the largest question can be about 32k tokens [00:30:40].
  - The state plus all questions can be about 64k. Beyond that, split into multiple calls [00:30:40].
  - Images and multimodal input are "not yet" supported [00:31:27].
  - Signups were paused because of demand [00:36:54].
- **Thresholds and confidence**:
  - Thresholds depend on the domain. Test on your own data [00:38:38].
  - A Noul threshold below 50% suggests a model weakness or a badly written question [00:38:38].
  - The API's confidence is a deterministic statistic over the probability map and mainly measures spread [00:40:09].
  - Confidence is misleading when several answers legitimately compete. In those cases take the top choice [00:40:09][00:41:42].
  - Alternative statistics: the raw top probability, top minus second, or top divided by second [00:41:42].
- **Human-tuned copy**:
  - Put all instructions, criteria and level definitions in one central, editable place, because rewording them gives large accuracy gains [00:27:44].
  - Coding agents compose questions well but write criteria poorly [00:26:13].
- **Auditability**: log or inspect every Jev call so you can debug the answers [00:26:13][00:27:44].
- **Cost and speed**: it is described as cheap enough to run on every agent step, unlike an extra LLM call [00:18:16][00:22:56]. About 100–150 ms per message for chat filtering [00:34:04]. No price figures were given.

## 4. Tools and interfaces shown

- **Jev API**: typed schemas, used by programmers or AI coding agents. There is no end-user app [00:03:42].
- **LangChain TypeSafe package**: a middleware for "auto mode" tool gating and a model-router middleware, configured with tools and instructions or criteria [00:21:18][00:22:56].
- **LangSmith tracing**: shows each Jev classifier call's inputs and outputs. It now renders each choice type readably instead of raw JSON [00:24:35][00:29:15].
- **Jevify skill**: a community prompt that lets a coding agent find LLM decision points that could be replaced by Jev [00:27:44][00:29:15].
- **Docs "model jaggedness" page**: lists known weak areas [00:43:01].
- **Discord and X**: community channels [00:47:26].
- No playground, compile tool or spreadsheet interface is shown in this video.

## 5. Implications for Jev Lab

- **Batch many questions per document in one call**: up to 100 questions per call, within the 64k total [00:12:06][00:30:40]. Jev Lab should bundle all of a user's questions into one call per document and split automatically when it nears the 32k/64k caps.
- **Token budget meter and auto-chunking**: show the size of the state and the largest question against 32k, and the total against 64k. For long documents, offer a trim or excerpt step [00:30:40][00:44:33].
- **Question-quality linting in the no-code editor**:
  - Warn on "or" in yes/no questions [00:15:16].
  - Warn on compound Scores [00:13:39].
  - Require a description for every Score level [00:13:39].
  - Warn on overlapping Choice options [00:12:06].
- **Central "question library" editing**: this matches the advice to keep all criteria in one tweakable place [00:27:44]. Add a clone-and-edit flow and re-run to compare versions.
- **Per-question threshold settings with result routing**:
  - Categorize results using a user-set threshold or statistic: top probability, margin, or confidence [00:41:42].
  - Don't treat low confidence as "uncertain" by default for multi-answer Choices [00:40:09].
  - Show the full probability distribution, not only the top pick.
- **Calibration view**: let users label a sample and check whether the thresholds fit their domain. The speakers say "test your data" [00:38:38], and the GitHub-labelling anecdote shows the need [00:43:01].
- **Audit log of every call**: store the state sent, the questions, the raw answers and the timestamp, and make them viewable [00:27:44].
- **Folder and background runs are feasible**: calls are cheap and fast enough for per-item, real-time use [00:34:04]. That supports watch-folder processing with a queue. Because state + all questions must fit in one call [00:30:40], each call covers one item, so throughput comes from running calls concurrently.
- **Score-based slider filtering** of results in the UI, as in the Twitch demo [00:34:04].
- **Optional LLM hand-off**: route items to Claude when prose or multi-step reasoning is needed [00:10:28][00:18:16].
- **Doom lesson on state variables**: warn when a variable adds bulky or low-value detail to the state [00:46:01].

## 6. Claims to treat with caution

- The speed and cost numbers (100–150 ms, "won't break the bank") are anecdotal, with no benchmarks or prices given [00:34:04].
- "Breakthroughs" and "secret sauce" in training on synthetic in-house data are unverified [00:37:45][00:38:38].
- The roadmap (longer context, multimodal, faster, cheaper) comes with no dates or promises [00:31:27].
- The context limits are described as "basically" 32k/64k and "slightly complicated". Check them against the docs [00:30:40].
- Allie hedged when citing whether the jaggedness page covers long contexts [00:43:01][00:44:33].
- The claims that "vast majority of automation will be machine-to-machine" and "every 5 minutes a new use case" are promotional framing [00:07:06][00:35:28].
- The demo model names (Luna, Sol) and the package names come from auto-captions and may be misspelled [00:24:35].
- The webinar is a joint promotional event by two partner companies [00:00:02].
