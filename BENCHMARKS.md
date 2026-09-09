# Raqmi benchmarks

This file keeps live provider measurements separate from deterministic scenario assumptions. The repository does not contain a billing export, a saturated GPU throughput run, or live per-case provider rows.

## LIVE model comparison

Captured from the uploaded Colab notebook's `LIVE BACKEND COMPARISON: CAPTURED` output:

| Metric | DeepSeek | ALLaM/vLLM |
|---|---:|---:|
| Mode | LIVE | LIVE |
| Model | `deepseek-v4-flash` | `humain-ai/ALLaM-7B-Instruct-preview` |
| Serving | DeepSeek API | vLLM, OpenAI-compatible local endpoint |
| GPU | Provider-managed / not reported | Tesla T4, FP16, 1,024 max context |
| Overall quality | 88.89% | 88.89% |
| Arabic quality | 85.71% | 89.29% |
| Safety slice | 100% | 100% |
| 54-case wall time | 71.97472727399986 s | 59.70825590300001 s |

The wall time is for this sequential Golden Set run in one Colab environment. It is not saturated tokens-per-second throughput. Only the listed slices were printed; intent, difficulty, English, token cost, and cache details are not available as captured live data.

## Deterministic cost and latency scenario

The notebook's 100-request FAQ traffic mix is 35 return-policy questions, 25 delivery questions, 20 headphone-price questions, 10 English return questions, and 10 English delivery questions. It compares repeated calls against an exact response cache.

| Metric | Before | After |
|---|---:|---:|
| Requests | 100 | 100 |
| Model calls | 100 | 5 |
| Exact cache hits | 0 | 95 |
| Scenario cost | 0.0275655 USD | 0.0018245 USD |
| p50 latency | 5.004244500019013 ms | 0.2 ms |
| Cached input ratio in this benchmark | 70.3653% | 43.0841% |
| Adjacent deterministic Golden verdict | 100.0% | 100.0% |

The printed cost reduction is 93.4%. The prices are transparent scenario assumptions, not real invoices:

```text
commercial input  = $2.00 / 1M uncached tokens
commercial output = $8.00 / 1M tokens
open-weight input = $0.35 / 1M scenario-equivalent tokens
open-weight output= $1.00 / 1M scenario-equivalent tokens
cached input discount = 75%
```

The benchmark's cost row is paired with the deterministic Golden Set verdict in the same cell. It does not prove that a live provider gives the same price, cache hit behavior, or quality after caching.

## Prefix and exact cache evidence

The prompt-prefix demonstration sends 12 different Arabic questions through `RuleBasedClient` with the same rendered grounding context. It prints `prompt cached-input ratio: 65.9%`. Because the demo client synthesizes its warm-prefix token count, this is instrumentation evidence, not live DeepSeek cache evidence.

The exact key contains model ID, prompt version, normalized text, language, and sampling parameters. The five near-miss pairs produce `near-miss wrong hits: 0/5`. The cache is not integrated into `ask()`, the historical key does not include a grounding revision, and no semantic tier has been calibrated on measured data.

## Fault and fallback timing

The deterministic reliability drill prints two scripted 429 failures then success on the third attempt, and a primary outage served by `openweight-fallback`. Those values are control-flow tests; they are not provider outage rates or production latency.

## Break-even status

The rubric asks for self-host break-even based on measured throughput and both comparisons. The uploaded evidence has only sequential Golden Set wall time and no token throughput, GPU utilization, host price, or provider billing. A defensible break-even number cannot be calculated from this artifact, so this repository leaves that requirement open rather than substituting a vendor figure or a scenario guess. The conditional routing recommendation in [DECISIONS.md](DECISIONS.md) is limited to observed quality and wall time.
