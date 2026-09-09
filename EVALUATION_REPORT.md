# Raqmi evaluation report

This report separates the earlier live-provider capture from deterministic and simulated measurements. The uploaded executed notebook is the source of truth. Local validation compiles and runs the default no-key path with network and process operations blocked; it does not rerun DeepSeek, vLLM, or a GPU.

## Evaluation goals

The harness checks whether an Arabic-first retail assistant can answer grounded policy and catalogue questions, protect order ownership, validate return requests, refuse prompt injection, escalate uncertainty, and survive bounded provider faults. It also checks regression behavior and reports cost/cache instrumentation.

## Dataset and slices

The unchanged Golden Set has 54 cases: 28 Arabic and 26 English. It covers FAQ, order status, return requests, blocked/authorization cases, and human escalation. Difficulty counts are easy 12, medium 16, hard 26; risk counts are low 11, medium 21, high 22. The high-risk slice is deliberately oversampled.

The rubric requires every intent stratum to contain at least eight cases. The historical `blocked` intent has six, while the other intent strata have at least eight. The set was not edited after evaluation to make this requirement appear complete.

The attack corpus has 32 bilingual injection cases. The legitimate corpus has 32 bilingual requests, including phrases containing “instructions,” “system,” and other deliberate traps.

## Deterministic harness results

These results come from the `RuleBasedClient` and deterministic application guards in notebook sections 9–15 and 17–18. They are repeatable offline checks, not live provider measurements.

| Check | Captured result | Evidence |
|---|---:|---|
| Attack cases blocked | 32/32 = 100% | §10, cell `52ef9833` |
| Legitimate cases blocked | 0/32 = 0% false positives | §10, cell `52ef9833` |
| Golden Set cases passed | 54/54 = 100% | §12, cell `cf88d2d3` |
| Arabic / English Golden slices | 100% / 100% | §12, cell `cf88d2d3` |
| High-risk safety slice | 22/22 = 100% | §12, cell `cf88d2d3` |
| Judge scaffold agreement / κ | 100% / 1.00, n=40 | §13, cell `b4666e9b` |
| Clean regression candidate | PASS | §14, cell `2a6b7cbc` |
| Seeded degraded FAQ candidate | BLOCK | §14, cell `2a6b7cbc` |

The safety denominator is all 22 high-risk cases, including authorized return actions as well as refusals. It must be read together with the separate 32-case attack block rate.

The judge result is a calibration-plumbing scaffold, not an actual calibrated LLM judge. Ten synthetic label/support tuples are repeated four times; `RuleBasedClient` receives the expected score through metadata and echoes it. No independent annotator labels and no live judge outputs were captured. The reported κ must not be used as evidence that a production judge is calibrated.

The regression gate compares language, intent, difficulty, risk, and safety slices. The seeded `faq.v0-degraded` prompt claims a 30-day return window and is blocked by the gate. The Golden Set and thresholds remain unchanged.

## Preserved LIVE provider comparison

The following exact aggregates were captured in the uploaded Colab run with `RUN_LIVE_GOLDEN=True`. They were not recomputed locally.

| Metric | DeepSeek | ALLaM/vLLM |
|---|---:|---:|
| Mode | LIVE | LIVE |
| Model | `deepseek-v4-flash` | `humain-ai/ALLaM-7B-Instruct-preview` |
| Overall quality | 0.8888888888888888 (88.89%) | 0.8888888888888888 (88.89%) |
| Arabic slice | 0.8571428571428571 (85.71%) | 0.8928571428571429 (89.29%) |
| Safety slice | 1.0 (100%) | 1.0 (100%) |
| Golden Set wall time | 71.97472727399986 s (≈71.97 s) | 59.70825590300001 s (≈59.71 s) |

ALLaM was served locally through the OpenAI-compatible vLLM endpoint on a Tesla T4 in Google Colab. The readiness output identifies the model and the provider-binding output identifies both routes. An ALLaM router smoke test returned `order_status` over HTTP.

The defensible conclusion is limited to this Golden Set and this environment: ALLaM matched DeepSeek in overall quality, scored higher on the Arabic aggregate, and completed the measured sequential evaluation faster. This is not a global model ranking.

The captured live cell printed only overall quality, Arabic quality, safety, and total wall time. It did not persist per-case rows, full intent/difficulty/risk slices, live token cost, or live prompt-cache usage. Those values are unavailable from the artifact and are not reconstructed here. Live extraction pass rates by language and a live native tool-call transcript are also absent.

## Tool and authorization evaluation

The historical application has three application-dispatched tools: `lookup_order` (read-only), `create_return` (side-effecting), and `escalate_to_human` (terminal). Session ownership is checked by deterministic code outside the model. The captured negative tests reject cross-user reads, cross-user returns, and wrong-item returns and log risk class plus iteration.

The historical `ask()` flow dispatches tools directly after routing. The OpenAI-compatible adapter sends only system/user messages and reads assistant text; it does not send tool schemas or consume provider `tool_calls`. Return extraction parses candidate fields in Python before calling the model and ignores the returned extraction text. The optional [native tool protocol](TOOL_CALLING.md) adds a strict, bounded, locally tested implementation after the live capture; it does not upgrade these historical results.

## Guard and output limitations

Input normalization and regex guardrails are effective on the finite corpus, but no finite corpus proves general prompt-injection immunity. The output canary detector is exact and the grounding check is intentionally numeric and narrow. It can miss wrong associations, such as a return-window claim using a number that appears elsewhere in the catalogue. Missing return reasons currently default to `other`; the historical code therefore can create a return when a stricter policy would ask for clarification.

The harness comment says each case gets fresh state, but global `RETURNS` and `ESCALATIONS` are not restored between rows. The row verdict still checks response fields and safety, but side-effect isolation is a known defect and is covered as an expected failure in local tests.

## Cost, latency, and cache evidence

The notebook's scenario benchmark runs 100 repeated FAQ requests:

| Scenario | Requests | Model calls | Cache hits | Cost (scenario USD) | p50 latency |
|---|---:|---:|---:|---:|---:|
| Before exact response cache | 100 | 100 | 0 | 0.0275655 | 5.004 ms |
| After exact response cache | 100 | 5 | 95 | 0.0018245 | 0.2 ms |

It prints 93.4% cost reduction beside a 100.0% deterministic Golden Set verdict. The prices (`$2.00/$8.00` per million commercial input/output tokens and `$0.35/$1.00` open-weight scenario equivalents), cache discount, and response-cache latency are assumptions in a deterministic benchmark, not invoices or live provider billing.

The prefix-cache proof prints a 65.9% cached-input ratio from `RuleBasedClient` usage fields. That client synthesizes a warm-prefix proportion; it is not a DeepSeek or vLLM cache measurement. The exact-cache near-miss test prints 0/5 wrong key collisions. The cache key includes model, prompt version, normalized text, language, and sampling parameters, but not a grounding/policy revision, and the cache is exercised in the benchmark rather than integrated into `ask()`. There is no measured semantic-cache tier.

## Reliability evidence

The scripted fault drill captures two 429 failures followed by a successful retry, and a primary outage followed by an open-weight fallback. These are deterministic `RuleBasedClient` faults, not production incidents. The live clients registered in the captured comparison are direct HTTP adapters; the live comparison itself is not wrapped by `ResilientClient`.

## Limitations and submission actions

The remaining evidence gaps are: live judge calibration; live language-split extraction/repair rates; native model-requested tools against a provider; the six-case blocked-intent stratum; complete live slices and cost; real provider cache usage; measured semantic-cache threshold; and measured GPU throughput/self-host break-even. The final Colab runtime must be restarted and run top-to-bottom by the owner after reviewing these gaps. No result in this report claims that work was completed when it was not.
