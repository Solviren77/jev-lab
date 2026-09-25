# Notes: TRYING JEV: The new STYLE of AI (The PrimeTime)

Source: https://www.youtube.com/watch?v=FQNftquDDaI (148 min livestream, uploaded 2026-09-18). Transcript is YouTube auto-captions; "Jev" also appears as "Jeff", "Jeb", "Gv", and "Noul" as "nule" ([02:19:37]). Most of the stream is chat banter unrelated to Jev (AI-safety commentary, Netflix stock, jokes), and this note leaves it out.

## 1. Summary

ThePrimeagen (The PrimeTime) live-codes a TypeScript "sidecar" that reads Balatro game state through a custom Lua mod ("god view") and asks Jev what to do next ([00:03:25], [00:16:38], [00:18:04]). He had only just got access and says he does not yet know the right way to use Jev ([00:37:27], [00:42:05], [00:45:00]). Most of the time goes on game plumbing that Claude-style coding agents write for him: button lists, click actions, and trimming the state ([00:36:06], [01:06:35], [01:38:36]). Jev gets past the splash screen and main menu, then makes poor card choices in the hand-selection phase ([01:00:00], [01:27:21], [02:05:58]). He ends by concluding that he needs a decision tree or behaviour tree of small questions, with Jev acting as a classifier ([02:11:52]–[02:19:37]).

## 2. Use cases demonstrated

- **Support-ticket urgency (earlier test, recalled).** The state was a message like "my payouts have been failing for three days" or "I've pooped my pants and I need help now". He asked a Choice question named "urgent" with options such as technical and interact ([00:21:19], [00:37:27]). He reports only that it was fast and "dirt cheap" ([00:22:53], [00:37:27]).
- **Balatro splash screen.**
  - First attempt: a single Choice "next move", with the instruction asking for the next action to start and win a game ([00:26:25], [00:32:02]). The options were badly formed (a stringified "mouse down" plus "unknown"), and Jev returned "unknown" with high confidence ([00:34:00], [00:50:14]).
  - With a "click" option, it chose to interact, at 26% confidence in one run ([00:36:06], [00:37:27]).
  - Once the wiring was fixed, Jev clicked through the splash screen ([01:00:00]).
- **Balatro main menu.** A Choice between Play and Quit. It returned Play at about 99% and Quit at 1% ([00:50:14], [00:52:09], [01:02:54]). A code bug executed both options rather than just the top one ([01:02:54], [01:04:55]). After the fix it pressed Play ([01:04:55]).
- **Dynamic button choices.** He turned every button on screen into a Choice option ("encode buttons") ([01:06:35]–[01:10:29]). Jev picked an overlay "back" button because the mod marked buttons hidden behind the overlay as enabled ([01:10:29], [01:12:24]). A lesson he draws here, via chat: if the state does not describe the screen accurately, Jev guesses ([01:14:55]). After further fixes it selected a blind and entered a round ([01:21:25], [01:27:21]).
- **Balatro hand selection.**
  - Given only buttons, it kept choosing "run info" ([01:36:39], [01:38:36]). Once card actions were added as options, it selected cards, including a king in one run ([01:40:41], [01:43:13]).
  - A strategy hint in the instructions led it to repeatedly sort by suit ([01:45:50], [01:47:50]).
  - Input was about 20–21k tokens of raw state before trimming ([01:58:02]).
  - A trimmed state followed, with the hand, selected cards and score, plays and discards left, chips needed, jokers, tarots, hand values, a hand guide and a rules "how to" of 500 words or fewer. With it, Jev still "selected the worst possible card" ([01:59:59], [02:02:06], [02:05:58], [02:07:55]).

## 3. How Jev is meant to be used (as stated or inferred on stream)

- **API shape.** `ask` takes a state and questions ([00:18:04]). State entries are key/string or JSON values ([00:18:04]).
  - Each question has a name, a type, an instruction (the question itself), criteria or an optional description, and options or outcomes ([00:19:35], [00:30:00]).
  - Types seen: new question, score question and choice question ([00:30:00]). He uses a "Jev latest" model identifier ([00:21:19]).
  - The answer returns probabilities per option plus a confidence value ([00:36:06], [01:02:54]).
- **No memory between calls.** Every call is a new prompt with no history, so rules and context have to go into the state each time ([02:16:08]).
- **State design.**
  - A huge raw JSON state produced bad results. He trimmed it to the fields that matter for the decision and dropped the deck, shop and discard pile ([01:52:00]–[01:58:02]).
  - He moved strategy hints from the instruction into the state ([01:47:50]).
  - The state must match reality: it should not offer disabled or hidden actions or misleading "reason" fields ([01:14:55], [01:33:07], [01:35:04]).
- **Question design.**
  - Choices should be dynamic, limited to the actions valid on the current screen, with a different question per phase ([00:43:38], [00:45:00], [01:27:21]).
  - Give options clear names; card IDs like "select 249" are unhelpful ([01:43:13]).
  - Chat mentioned a Jev-team skill for writing choice questions ([01:45:50]).
- **Hierarchy.** Break the problem into a decision tree or state machine: a high-level choice (select, play or discard), then lower-level choices, then a Noul such as "play this hand?" ([02:13:47]–[02:19:37]). He doubts a whole turn can be done in one query ([02:19:37]). He called Jev "really" a classification engine ([02:11:52]).
- **Combining with an LLM.** A coding LLM builds the harness, the state reducer and the rules text. Jev only makes the decision ([00:36:06], [01:59:59], [02:03:49]).
- **Speed and cost.**
  - He says decisions take about 200 ms ([01:29:22]), yet one call ran slowly enough to hit the game's action timeout ([00:52:09]).
  - Cost is "dirt cheap" ([00:37:27]), with an initial $5 credit mentioned from chat ([00:42:05]).
- **Limits.**
  - Not multimodal yet ([00:43:38]).
  - It does not chat or produce text ([01:35:04]).
  - It struggled to optimise score ([02:19:37]).
  - No routing on confidence thresholds, many items per call, or parallel batching was shown.

## 4. Tools and interfaces shown

- **TypeScript SDK** ("typesafe" package, `ask`, question type helpers). He explores the types in the editor ([00:18:04], [00:30:00]).
- **Custom harness.** A Balatro Lua mod plus a "sidecar" TypeScript loop and a god-view JSON dump, run through `just` recipes and inspected with `jq` ([00:03:25], [00:28:15], [00:30:00], [01:04:55]).
- **Answer output.** Answers are logged as JSON: choice, probabilities, confidence and input tokens ([00:36:06], [00:52:09], [01:58:02]).
- **Coding agent.** An AI coding agent (a "4.6 fast" model) writes most of the glue code ([00:42:05], [00:54:12]).
- **Others' demos.** Official launch tweets show Jev playing Mario through structured game state, and Doom is claimed ([02:21:13]). No playground, compile tool or spreadsheet was shown.

## 5. Implications for Jev Lab

- **Cheap, repeated calls.** Every call is stateless, so Jev Lab should keep the shared context (a rules or glossary "how to") as a reusable state block and attach it to each call automatically ([02:16:08], [02:07:55]).
- **State trimming.** Offer a state preview with a token count and let the user pick fields or excerpts. Large raw input hurt accuracy and cost ([01:52:00], [01:58:02]).
- **Staged questions.** Support multi-step flows where the answer to one question decides the next question or its options. For example, classify the document type first, then ask type-specific questions ([02:16:08]–[02:19:37]).
- **Dynamic options.** Let the options for a question come from a variable or an earlier result instead of a fixed list ([00:45:00], [01:06:35]).
- **Option quality checks.** Warn about empty, duplicate, "unknown" or opaque ID-style option labels ([00:50:14], [01:43:13]).
- **Only the top answer acts.** Show the top answer with its probability and confidence. Any automation (moving files, tagging) acts only on the top choice and only above a user-set threshold. The stream hit a bug that executed every option ([01:02:54], [01:04:55]).
- **Instructions versus context.** Keep the question separate from the context in the UI. Moving hints between the two changed behaviour ([01:47:50]).
- **Timeouts and latency.** Show per-call latency and handle slow calls gracefully in background folder runs ([00:52:09]).
- **Folder and batch runs.** Nothing on stream bears on this directly. It was all one state per call, so this video does not support many-items-per-call designs.

## 6. Claims to treat with caution

- The 200 ms decision time is the streamer's impression, not a measurement, and a slow call was also observed ([01:29:22], [00:52:09]).
- Jev plays Mario or Doom: the Mario clip comes from the official launch, and the Doom claim was unverified. The streamer found the "Doom" result was an unrelated person named Jeff ([00:01:49], [02:21:13]).
- The "Jevons paradox" name origin and the pronunciation "Gv" come from chat ([00:01:49], [01:35:04]).
- "Dirt cheap" and the $5 credit are anecdotal, with no pricing given ([00:37:27], [00:42:05]).
- Confidence values sometimes contradicted the outcome: "very high confidence" in "unknown" ([00:50:14]).
- The streamer is a new user who admits he may be using it wrongly. Poor Balatro results reflect his harness and question design as much as the model ([00:45:00], [01:14:55], [02:19:37]).
- "Jev is a classification engine" and "basically a decision tree" are opinions from the streamer and chat ([02:11:52], [02:13:47]).
