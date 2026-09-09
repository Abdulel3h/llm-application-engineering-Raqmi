# Five-stage guardrail pipeline

Section 7 of the notebook is the guard that produced the captured 32/32 and 0/32 numbers. It is unchanged. Section 7A separates the wall into five independently testable guard stages around the router/LLM processing core, and adds PII masking, a paraphrase classifier and a wider outbound wall.

| # | Stage | Kind | Function | What it does |
|---|---|---|---|---|
| 1 | Normalization | guard | `stage_normalize` | Unicode NFKC, zero-width and bidi/format control removal, whitespace collapse |
| 2 | Deterministic guard | guard | `stage_deterministic_guard` | the original bilingual direct-injection patterns — literally `input_guard`, unchanged |
| 3 | PII masking | guard | `stage_mask_pii` | masks Saudi mobile numbers and e-mail addresses before any text reaches a provider |
| 4 | Safety classifier | guard | `stage_classify_safety` | deterministic lexical injection/exfiltration classifier for paraphrases stage 2 does not literally match |
| — | Router / LLM | **processing core** | `ask` | intent routing, grounded answer, authorization, tool dispatch |
| 5 | Output guard | guard | `stage_output_guard` | outbound wall: canary, PII, internal-error and instruction-relay leakage |

`guard_inbound()` composes stages 1–4 and returns an `InboundDecision` with the masked text and a per-stage trace. `ask_guarded()` runs `guard_inbound → ask → stage_output_guard` and returns the same `Reply` type, so nothing downstream changes.

## Numbering note

Some course material numbers the same pipeline in six steps, with *Router/LLM* as step 5 and *Output Guard* as step 6. The mapping is exact:

| This document | Course six-step numbering |
|---|---|
| Stage 1–4 | steps 1–4 |
| Router / LLM processing core | step 5 |
| Stage 5 (`stage_output_guard`) | step 6 |

The count differs only because the router is not itself a guard. There are five guard stages either way.

## Why stage 4 is deterministic

The classifier sits on a safety-critical, always-on, pre-provider path. A deterministic lexical classifier is auditable line by line, adds no latency, no cost and no availability dependency, and cannot itself be prompt-injected — none of which is true of a model-based classifier on this path. It also keeps the notebook's no-key **Run all** honest: there is no hidden model call inside a guard.

It fires only on signal combinations, not single keywords:

| Rule | Trigger | Required companion |
|---|---|---|
| `jailbreak_mode` | named jailbreak mode | — |
| `third_party_data_request` | another customer's data | — |
| `instruction_override` | override verb (`ignore`, `forget`, `تجاهل`, `انس`, …) | system-scoped target or bulk access |
| `privileged_role_request` | privileged role assumption | system target, bulk access, or third-party data |

The companion requirement is what keeps the false-positive rate at zero: a *system-scoped* target means "your instructions", "the previous instructions", "تعليمات النظام" — never the bare word "instructions". That is why the legitimate corpus's traps (`What are the instructions for returning a defective item?`, `وش تعليمات إرجاع المنتج التالف؟`, `Skip the gift wrap instructions for order 1024`, `تجاهل رسالتي السابقة، كم سعر السماعة؟`) all pass.

## PII masking rules

A Saudi mobile number needs at least nine digits before it can be masked, because order ids are four digits and prices are two or three. Arabic-Indic (`٠-٩`) and extended Arabic-Indic (`۰-۹`) digits are treated as digits.

```text
رقمي 0551234567 وين طلبي؟   →   رقمي [PHONE_REDACTED] وين طلبي؟
Where is order 1024? It costs 249 SAR.   →   unchanged
```

Masking runs **before** the message reaches any provider, so a phone number in a live request never leaves the application. It also runs on the outbound side: a reply containing an e-mail or mobile number is redacted and categorised `pii_leak`.

## Outbound wall categories

| Category | Detects |
|---|---|
| `system_prompt_leak` | the exact prompt canary (the original §7 check, unchanged) |
| `internal_error_leak` | tracebacks, `File "...", line N`, exception class names, provider endpoints, `Bearer` headers, credential-shaped env var names, object addresses |
| `instruction_leak` | any distinctive line of any registered prompt version, derived from `PROMPTS` at call time so later prompt versions are covered automatically |
| `pii_leak` | mobile numbers and e-mail addresses in the reply |

## Measured results

All numbers below are produced by the notebook itself and reproduced by the offline test suite. They are deterministic and require no provider.

| Measure | Result | Where |
|---|---|---|
| Attack block rate, five-stage wall, original 32-case corpus | **32/32 = 100%** | §10A |
| False positives, original 32-case legitimate corpus | **0/32 = 0%** | §10A |
| Stage-4 classifier alone on the same attack corpus | 22/32 | §10A |
| Paraphrased attacks stage 2 does not match, blocked by stage 4 | 10/10 | §7A stage-4 cell |
| Legitimate paraphrases reusing classifier vocabulary | 0/12 blocked | §7A stage-4 cell |
| Golden Set replies changed by adding the pipeline | **0 of 56** | §12B |
| Outbound leak classes blocked | 4 categories, 11 demo cases | §7A stage-5 cell |

The stage-4-alone figure is reported deliberately: the classifier is an *addition* to the pattern guard, not a replacement for it, and 22/32 is what it achieves on its own.

## Tests

`tests/test_guard_pipeline.py` covers each stage in isolation and then the wall as a whole: normalization idempotence, stage-2 byte-equality with `input_guard`, Arabic and English PII (including Arabic-Indic digits and bare nine-digit mobiles), retail-identifier preservation across the whole Golden Set, classifier attacks and legitimate vocabulary, every outbound leak class, prompt versions registered after the guard cell ran, the stage-ordered trace, and Golden Set parity between `ask()` and `ask_guarded()`.

`tests/test_tool_calling.py::GuardPipelineIntegrationTests` additionally proves the native tool loop uses the wall: a phone number is masked before the provider request is built, a paraphrased injection is blocked before any provider call, and a relayed internal error is stopped on the way out.

## Scope and limits

- The classifier is lexical. It generalises across paraphrase and Arabic spelling variants, but it is not a semantic model and will not catch a novel attack written entirely outside its vocabulary.
- `instruction_leak` matches whole prompt lines of 24 characters or more. A model that paraphrases the system prompt rather than quoting it is not detected.
- PII coverage is mobile numbers and e-mail addresses. National IDs, IBANs and postal addresses are not covered.
- These stages were validated offline. No live-provider measurement of the pipeline is claimed.
