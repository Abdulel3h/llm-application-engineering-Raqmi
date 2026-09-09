# Raqmi evaluation report

The official notebook `Raqmi_Capstone.ipynb` (SHA-256 `cffa505e0d2289f1654651d79b36b5edc55fe54b3d25003bd88fafea9c6eb345`) is the owner's final executed Google Colab run: 87 cells, all 47 code cells executed sequentially (counts 1–47), against live DeepSeek and live ALLaM served by vLLM on a Tesla T4. Every result below is read from that run.

This report keeps three categories strictly apart:

- **LIVE** — measured against a real provider in that Colab run.
- **DETERMINISTIC** — produced by the no-key rule-based client; reproducible, but not a model measurement.
- **SCENARIO** — arithmetic over stated assumptions; not provider billing.

## Dataset

The Golden Set contains **56 cases**: 29 Arabic, 27 English; intents order status 14, FAQ 13, return 12, escalation 9, blocked 8; difficulty easy 12, medium 16, hard 28; risk low 11, medium 21, high 24. Every marginal stratum meets the minimum of eight, and safety is deliberately oversampled.

A case passes when its expected blocked status, intent and required answer substring all match. This is an exact-case harness, not a full semantic-quality score. Expected labels, risk labels, safety definitions and thresholds are unchanged from the original design.

Separate corpora: 32 bilingual attacks and 32 legitimate requests with deliberate traps; 20 structured-output cases; 36 judge reference cases.

## LIVE provider measurements

### Backend comparison

| Metric | DeepSeek | ALLaM/vLLM |
|---|---:|---:|
| Model | `deepseek-v4-flash` | `humain-ai/ALLaM-7B-Instruct-preview` |
| Overall quality | **91.07%** (51/56) | **91.07%** (51/56) |
| Arabic slice | **89.66%** (26/29) | **89.66%** (26/29) |
| High-risk safety | **100%** (24/24) | **100%** (24/24) |
| Sequential wall time | **60.95 s** | **63.91 s** |

Five cases failed per provider, all FAQ, **none high-risk**. Each failed row is printed with its language, expected and observed intent, blocked status, guard category, reply, the router label the model proposed and the deterministic routing policy's decision. Safety did not depend on the model getting routing right: a message naming an order the session does not own is always routed to the ownership check.

### Structured output

20 cases against DeepSeek in 23.79 s, 10 per language. Each language: **5 first-pass valid, 1 valid after repair, 4 escalated**; **10/10 matched the designed outcome**. Safety invariants passed — no invented order id, product, reason or owner. Repair may fill a missing product only when the authenticated customer's order contains exactly one item; it can never supply an order, an owner, or an unsupported reason.

### LLM-as-a-Judge

**n = 36, agreement = 0.778, Cohen's κ = 0.667**, target κ ≥ 0.60 **met**. Eight disagreements are printed in full. The 36 reference labels were written against a fixed rubric before any judge ran and are frozen by SHA-256, re-checked after the run; the judge receives only the question, evidence, candidate answer and rubric. `JUDGE_IS_REGRESSION_GATE` is `False` — §14's gate stays deterministic.

### Native tool calling

| Scenario | Outcome |
|---|---|
| Authorized lookup (order 1024) | model issued `lookup_order`; executed; `role: tool` result returned; model wrote the final answer |
| Cross-user lookup (order 5521) | **DENIED** with `authorization_denied`; nothing executed; no other customer's data in the reply |
| Authorized return | model issued `lookup_order`, then `create_return`; **`returns_created = 1`**, **`return_id = R-1001`**, canonical product `headphones` |

No tool-call diagnostics were recorded: every provider tool call passed envelope normalization, whitelist, strict Pydantic validation and catalogue canonicalization. In this run DeepSeek looked the order up first and emitted an already-lowercase product, so `product_input` equalled `product_canonical`; the case-mismatch path that previously failed is covered deterministically by the offline transcript and the test suite.

## DETERMINISTIC results

| Check | Result |
|---|---:|
| Golden Set (rule-based client) | 56/56 |
| High-risk safety | 24/24 |
| Attacks blocked | 32/32 (100%) |
| Legitimate false positives | 0/32 (0%) |
| Five-stage pipeline | 100% block, 0% false positives, 0 of 56 answers changed |
| Regression gate: clean / seeded degraded prompt | PASS / BLOCK |
| Judge plumbing scaffold | κ = 1.00, n = 40 |
| Four-part demo | PASS |

**The κ = 1.00 scaffold is not a judge result.** It repeats ten synthetic label/support tuples four times and echoes the score back through the rule-based client; it verifies the calibration plumbing only. The real judge measurement is the LIVE κ = 0.667 above.

## SCENARIO experiments — not billing

100-request FAQ traffic mix: 100 → 5 model calls, 95 exact-cache hits, scenario cost 0.0275655 → 0.0018245 USD (**93.4%** reduction) shown beside a 100% deterministic Golden verdict; p50 latency 5.005 ms → 0.2 ms; simulated prefix-cache ratio **65.9%**; 0/5 near-miss key collisions.

Prices, token estimates, the cached-input discount and the cache-hit latency are stated assumptions. The prefix ratio is synthesized by the deterministic client. **None of this is provider usage or an invoice**, and the cache is benchmarked separately from `ask()`.

## Reliability

Scripted drills only: two 429 responses followed by success, and a primary outage served by the open-weight fallback. These are control-flow tests with deterministic clients; the live comparison used each provider directly and did not exercise real failover.

## Verification performed locally

240 tests pass; the offline validator executes all 47 code cells with network and process operations blocked, confirms the deterministic 56/56 and 24/24 results, and verifies that the captured LIVE markers and every cell's saved output are unchanged. The secret scan reports no findings. Local verification uses deterministic and scripted providers; it does not re-run DeepSeek, ALLaM or a GPU.

## Limitations

- Cost, cache and latency scenario figures are assumptions, not provider billing.
- No measured self-host break-even; sequential wall time is not saturated throughput.
- ALLaM's native tool-call parsing is untested; the live tool section targets DeepSeek.
- Grounding and catalogue scope are intentionally narrow; PII masking covers Saudi mobile numbers and e-mail addresses; the safety classifier is lexical, not semantic.
- The judge corpus is small and single-annotator, with no second-annotator study.
- The Golden metric is exact-case; five FAQ cases failed per provider.
- No complete live per-case export beyond the printed failed-case report, no complete attempt metering, and no calibrated semantic-cache tier.

[The rubric map](RUBRIC_MAP.md) ties each requirement to its notebook section, file and captured evidence.
