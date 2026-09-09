# Raqmi benchmarks

Every number here is read from the official executed notebook, `Raqmi_Capstone.ipynb` (SHA-256 `cffa505e0d2289f1654651d79b36b5edc55fe54b3d25003bd88fafea9c6eb345`), captured in one sequential Google Colab run with live DeepSeek and live ALLaM/vLLM.

**Captured provider measurements and deterministic scenario assumptions are kept apart throughout. Scenario costs are not provider invoices.**

## LIVE Golden Set comparison

| Metric | DeepSeek | ALLaM/vLLM |
|---|---:|---:|
| Mode | LIVE | LIVE |
| Model | `deepseek-v4-flash` | `humain-ai/ALLaM-7B-Instruct-preview` |
| Overall quality | 0.9107142857142857 (**91.07%**, 51/56) | 0.9107142857142857 (**91.07%**, 51/56) |
| Arabic slice | 0.896551724137931 (**89.66%**, 26/29) | 0.896551724137931 (**89.66%**, 26/29) |
| High-risk safety | 1.0 (**100%**, 24/24) | 1.0 (**100%**, 24/24) |
| Sequential wall time | **60.947293607000006 s** | **63.910626944 s** |

Both providers ran the same 56-case Golden Set in the same Colab session. ALLaM was served locally by vLLM on a Tesla T4 (FP16, 1024-token context, eager mode).

Wall time is **sequential end-to-end evaluation time**, not saturated throughput: no batching, no concurrency, and DeepSeek's figure includes network latency while ALLaM's includes local GPU inference. It does not support a cost-per-token or break-even claim.

### Failed cases

Five of 56 cases failed for each provider; **no high-risk case failed for either** (both safety slices 24/24).

| Provider | Failed cases | Observed |
|---|---|---|
| DeepSeek | كم مدة التوصيل؟ · كم سعر السماعة؟ · كم ضمان الساعة الذكية؟ · How long does delivery take? · Can a defective product be returned? | all routed to `escalate` |
| ALLaM | كم مدة التوصيل؟ · هل المنتج التالف قابل للإرجاع؟ · كم سعر الشاحن؟ · Can a defective product be returned? · How much is the USB-C charger? | `order_status`, `faq`, `escalate` |

All ten are FAQ cases. The harness scores an exact-case match on intent, blocked status and a required substring, so a grounded answer that escalates instead of quoting the number is counted as a failure.

## Other LIVE sections

| Section | Captured measurement |
|---|---|
| Guard suite | 32/32 attacks blocked (100%); 0/32 legitimate requests blocked (0% false positives) |
| Five-stage pipeline | same 100% / 0%; 0 of 56 Golden answers changed |
| Structured output | 20 cases, 10 per language, DeepSeek, 23.79 s; each language 5 first-pass valid, 1 valid after repair, 4 escalated; 10/10 designed outcomes matched; safety invariants PASS |
| LLM-as-a-Judge | n = 36, agreement 0.778, Cohen's κ 0.667; target 0.60 met; 8 disagreements; not the regression gate |
| Native tool calling | authorized lookup executed; cross-user lookup denied by authorization; authorized return `returns_created = 1`, `return_id = R-1001`, canonical product `headphones`; total 6.26 s; no tool-call diagnostics recorded |

## Deterministic scenario experiments — not provider billing

These come from the deterministic harness with transparent, stated assumptions. They are **not** measured provider usage or invoices.

| Scenario measure | Value |
|---|---:|
| Requests in the FAQ traffic mix | 100 |
| Model calls before / after caching | 100 / 5 |
| Exact-cache hits | 95 |
| Scenario cost before / after | 0.0275655 / 0.0018245 scenario USD |
| Scenario cost reduction | **93.4%** |
| p50 latency before / after | 5.005 ms / 0.2 ms |
| Evaluation verdict beside the saving | 100% deterministic Golden |
| Simulated prefix-cache ratio | **65.9%** |
| Exact-cache near-miss collisions | 0/5 |

Assumed prices: commercial input $2.00 / 1M uncached tokens, output $8.00 / 1M; open-weight input $0.35 / 1M scenario-equivalent, output $1.00 / 1M; cached-input discount 75%. The prefix-cache ratio is synthesized by the deterministic client, not read from provider usage. Latency figures are the deterministic harness's own timings, not provider latency.

## What is not measured

- No provider billing, token accounting from invoices, or measured cache-hit economics.
- No self-host break-even: that needs saturated throughput, GPU-hour pricing and provider rates, none of which were measured.
- No calibrated semantic-cache tier; the exact cache is benchmark-only and separate from `ask()`.
- ALLaM's native tool-call parsing was never exercised; the live tool section targets DeepSeek only.
