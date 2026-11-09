# GPT-OSS 120B preliminary reply evaluation

**Run date:** 2026-11-09
**Provider/model:** Groq, `openai/gpt-oss-120b`
**Artifact:** [`gpt_oss_120b_evaluation.json`](gpt_oss_120b_evaluation.json)

## Purpose and method

This is a preliminary model-only check using the 10 synthetic held-out prompts
in `finetune_test.jsonl`. Each request used that case's existing system prompt
and user message, with `temperature=0.2`, `reasoning_effort=low`,
`include_reasoning=false`, and a 512-token completion budget. The saved JSON
contains every prompt, generated answer, reference answer, and finish reason.

The previous OpenAI fine-tuned model,
`ft:gpt-3.5-turbo-0125:personal::DqH2I32e`, was also checked. OpenAI returned
HTTP 404 and said the model has been deprecated, so a live head-to-head test
could not be performed. The reference answers in the JSON are dataset targets,
not newly generated answers from that old model.

This run bypassed GAIDA's live intent detection, full production system prompt,
few-shot retrieval, crisis routing, deterministic safety checks, and streaming
path. It does not evaluate crisis handling or prove that GPT-OSS is better than
the old fine-tune.

## Results

- **10/10** requests returned non-empty text and ended with `finish_reason=stop`
  at the 512-token budget.
- **10/10** replies asked one follow-up question.
- **10/10** replies matched the language of the prompt: English for English
  messages and Filipino/Taglish for the three Filipino/Taglish messages.
- Replies were warm and relevant overall, but the seven distress prompts all
  received a grounding suggestion. This is partly explained by the held-out
  prompt itself: its system instruction explicitly tells the assistant to
  “Offer a simple grounding tip.” The test therefore does not show that GPT-OSS
  would independently choose a breathing exercise in the full production flow.
  The answer to “wala na akong gana mag-aral” also suggested walking outside,
  an action that may not fit the student's situation.
- No crisis prompts were included, so crisis safety remains unevaluated here.

## Interpretation

GPT-OSS can produce usable text when given enough completion budget; the earlier
empty stream was consistent with the app's 110–160 token limit being consumed
before a final answer appeared. This small test suggests the model follows
language matching and one-question instructions. Its tendency to repeat
grounding advice cannot be separated from the explicit grounding instruction in
this test prompt; production-flow evaluation is needed to assess that behavior.

Treat this as a **small preliminary quality review**, not a statistical
comparison or clinical validation. The 10-item set is too small and too
low-severity to support a general safety or superiority claim. A counselor
should review a larger set—including crisis behavior through GAIDA's actual
crisis route—before the system is used with participants.
