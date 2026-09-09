# Raqmi architecture decisions

These decisions describe the implemented application and the trade-offs visible in the supplied notebook. They do not invent a development history that the upload cannot prove.

## ADR-001 — Router-first instead of agent-first

Retail requests fall into stable FAQ, order-status, return, and escalation intents. The router sends FAQ traffic to grounding and bounds transactional workflows. An agent loop would add latency and more failure modes without evidence that this domain needs open-ended planning.

## ADR-002 — One `LLMClient` boundary

DeepSeek and ALLaM/vLLM are both represented by the same request/response boundary and OpenAI-compatible adapter. The application can switch a configured backend without importing provider SDKs into business logic. The deterministic client keeps the notebook runnable without a key.

## ADR-003 — Authorization outside the LLM

`Session.authorize_order()` compares the authenticated session identity with the order owner before both reads and mutations. The model never supplies the user identity or decides ownership. Product membership is checked before creating a return.

## ADR-004 — Human escalation for uncertainty

Unsupported or disputed cases terminate in `escalate_to_human()`. This avoids inventing catalogue facts or silently approving sensitive actions. The current escalation record is fictional in-memory data and does not call an external support system.

## ADR-005 — Exact cache before semantic cache

Exact matching keeps personalized and near-miss retail questions from sharing a response accidentally. The notebook proves five exact-key near misses produce zero collisions. A semantic tier would need a measured threshold and a held-out wrong-hit evaluation; none was captured, so it is not enabled.

## ADR-006 — Open-weight ALLaM for Arabic-first evaluation

ALLaM was served behind vLLM so the same application boundary could compare a local open-weight route with DeepSeek. In the captured 54-case run it matched overall quality, had a higher Arabic aggregate, and finished faster. That observation is limited to the measured environment and does not establish global superiority.

## ADR-007 — Explicit live opt-in during finalization

The uploaded notebook had `RUN_LIVE_GOLDEN=True` and auto-started GPU/provider setup. For a stranger's default Run all, this could cause API charges, model downloads, or a missing-GPU failure. Finalization adds `ENABLE_LIVE_BACKENDS=False` and derives the live flag from it. The earlier live outputs, Golden Set, prompts, thresholds, and application handlers remain preserved; the owner enables live mode deliberately for a fresh Colab capture.

## ADR-008 — Native tool protocol as a post-capture supplement

The historical `ask()` path dispatches application tools after model routing and does not consume native `tool_calls`. A separate `raqmi_tool_calling.py` module implements strict schemas, provider tool definitions, tool-result messages, authorization, bounded iterations, and negative tests. It is kept separate because changing the captured notebook after the live run would make its scores ambiguous. The supplement is not claimed as live-provider evidence.

## Trade-off recorded

The final packaging favors a small, reproducible default and preserved evaluated evidence over a large refactor of the working notebook. That leaves known defects—numeric-only grounding, state accumulation during evaluation, and missing live native-tool/judge evidence—visible for submission review instead of changing behavior and silently invalidating the historical comparison.
