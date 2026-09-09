# Raqmi evaluation report

The latest uploaded executed notebook, `Raqmi_Capstone_ALLaM_vLLM_FIXED(1).ipynb`, is the source of truth. This report separates **its captured results** from **post-capture offline verification**. Local tests do not rerun DeepSeek, ALLaM, vLLM or a GPU, and the saved live metrics do not validate subsequent code fixes. See [source provenance](SOURCE_PROVENANCE.md).

## Goals and dataset

Evaluation checks bilingual retail answers, intent routing, order ownership, return validation, refusals, escalation and fault handling. The Golden harness calls the actual `ask()` pipeline. A row passes when its expected blocked flag, intent and required answer substring match; this is an exact-case metric, not a comprehensive factual-quality score.

| Dimension | Latest Golden Set counts |
|---|---|
| Total / language | **56** / Arabic **29**, English **27** |
| Intent | FAQ 13; order status 14; return request 12; escalation 9; blocked 8 |
| Difficulty | Easy 12; medium 16; hard 28 |
| Risk | Low 11; medium 21; high 24 |

All marginal strata now contain at least eight cases. The latest upload adds one Arabic and one English blocked case to the prior capture, leaving all prior case expectations unchanged. This change and the new live run came from the user's new source artifact; the finalization agent did not alter labels or thresholds to improve results.

The separate guard datasets contain 32 bilingual attacks and 32 legitimate requests, including deliberate traps with words such as “instructions” and “system.” Safety is oversampled in the Golden Set. Its reported safety denominator is **all 24 high-risk cases**, including authorized returns; it is different from the 32-case attack block rate. Expectations are author-defined and should be reviewed by the owner before submission.

## Captured deterministic results

| Check | Latest captured result | Notebook section / cell ID |
|---|---:|---|
| Attacks blocked | 32/32 = 100% | §10 / `52ef9833` |
| Legitimate prompts blocked | 0/32 = 0% false positives | §10 / `52ef9833` |
| Golden Set passed | 56/56 = 100% | §12 / `cf88d2d3` |
| Arabic / English slices | 100% / 100% | §12 / `cf88d2d3` |
| High-risk safety slice | 24/24 = 100% | §12 / `cf88d2d3` |
| Synthetic judge agreement / κ | 100% / 1.00, n=40 | §13 / `b4666e9b` |
| Clean / degraded regression candidate | PASS / BLOCK | §14 / `2a6b7cbc` |

These use deterministic guards and `RuleBasedClient`. The judge is a **calibration-plumbing scaffold**: ten synthetic label/support tuples repeated four times, with expected scores passed through metadata and echoed. There are no independent answer/evidence judgments by a live model. Its κ=1.00 does not establish calibrated LLM judgment.

The regression gate is deterministic and does not use this judge. It checks language, intent, difficulty, risk and safety slices. The degraded prompt claims a 30-day return window; it fails the FAQ slice and is blocked. In the new capture the degraded Arabic/English pass rates are 0.7586206896551724 and 0.7777777777777778; clean slices are 1.0.

## Captured LIVE comparison — latest upload

Both providers ran the same 56-case set with `RUN_LIVE_GOLDEN=True`. These exact values are preserved from §16, cell `238a9f1b`:

| Metric | DeepSeek | ALLaM/vLLM |
|---|---:|---:|
| Mode | LIVE | LIVE |
| Model | `deepseek-v4-flash` | `humain-ai/ALLaM-7B-Instruct-preview` |
| Overall quality | 0.8928571428571429 (**89.29%**) | 0.8928571428571429 (**89.29%**) |
| Arabic | 0.8620689655172413 (**86.21%**) | 0.896551724137931 (**89.66%**) |
| High-risk safety | 1.0 (**100%**) | 1.0 (**100%**) |
| Golden Set wall time | 67.33267155800013 s (**67.33 s**) | 60.25017996800011 s (**60.25 s**) |

ALLaM ran through a local OpenAI-compatible vLLM endpoint on a Tesla T4 in Colab, with FP16, 1,024-token context and eager mode. The upload captures model readiness, provider binding and a successful ALLaM router smoke test.

**For this Golden Set and environment, ALLaM matched overall quality, scored higher on the Arabic aggregate, and completed the sequential evaluation faster.** This is not a global model ranking or a measured economic advantage.

Each provider passes 50/56 cases under the exact-case harness, so six live rows fail for each provider. The capture does not persist failed-case identities or per-case predictions, so those six rows cannot be diagnosed from the saved aggregate. The two added blocked cases terminate in the input guard before a model call. The result is limited to this Golden Set and environment.

The latest capture prints overall, Arabic, high-risk safety and wall time only. It does not persist per-case predictions, failed-case identities, full intent/difficulty/risk live slices, token cost or real cache ratios. Those values are not invented or attributed to this run. Live model-extraction pass rates and native tool-call transcripts are also absent.

## Colab execution and compatibility evidence

The latest bootstrap (`d1f953e3`) captures vLLM installation, TorchAudio repair, successful CUDA-13 checks in a fresh subprocess, and `ALLaM/vLLM READY`. However, the notebook-kernel diagnostic (`da57f2b3`) reports PyTorch CUDA 13.0 versus TorchAudio CUDA 12.8. The subsequent ALLaM smoke and live comparison succeed. The artifact is consistent with a working new server process while stale package state remains in the notebook kernel; this is an explanation, not proof that every compatibility check passed.

The captured harness is execution count 30 and the live comparison count 31, after the four-part demo count 29. The artifact does **not** prove a single fresh, uninterrupted top-to-bottom run. Preserve the warning and perform a fresh final Colab verification before submission.

## Tools, safety and post-capture verification

The captured application dispatches Python tools after routing. `lookup_order`, `create_return` and `escalate_to_human` span read-only, side-effecting and terminal risk classes. Ownership and product membership are checked by application code using the authenticated session. The saved negative tests reject cross-user reads, cross-user returns and wrong-item returns, with risk/iteration logs.

Historical return extraction parses and validates local fields before making a model call whose extraction response is ignored. It is not a captured model validate → retry → repair workflow. The separate [native tool module](TOOL_CALLING.md) implements a model-requested protocol after capture; its tests use mocked responses. It is not integrated into the captured `ask()`/Golden evaluation, and no live-provider validation is claimed.

Four regression tests originally exposed actual defects. Their failure was **not intentional** and was not an accepted demonstration scenario. The finalization work addresses the application rather than relaxing assertions or changing Golden expectations:

| Regression test | Actual defect | Intentional? | Correction / verification status |
|---|---|---|---|
| `test_malformed_http_response_triggers_fallback` | Malformed successful HTTP responses could escape as parsing errors rather than boundary faults. | No | Map malformed response shapes to `LLMFault`; full test suite PASS. |
| `test_grounding_rejects_wrong_fact_association` | A number present elsewhere in the catalogue could incorrectly justify a different retail fact. | No | Check domain-specific numeric relationships; full test suite PASS. The detector remains narrow. |
| `test_missing_reason_requires_clarification` | An absent return reason defaulted to `other`, allowing action without clarification. | No | Require a supplied reason before creating a return; full test suite PASS. |
| `test_golden_run_restores_transaction_state` | Global return/escalation stores leaked evaluation side effects between cases and after a run. | No | Restore state per case and in failure cleanup; full test suite PASS. |

The preserved live scores describe the pre-fix implementation. Any final passing local result belongs to the amended application and must be kept separate from those scores.

Post-capture verification ran the offline notebook validator and the full 52-test suite: **52/52 passed**, including the four former regression gaps. The validator compiled and executed all 26 code cells with network/process operations blocked, confirmed deterministic 56/56 and 24/24 high-risk results, and verified that the saved live comparison, outputs and execution counts were unchanged. No live provider or GPU was rerun locally.

## Cost, cache and reliability

The latest captured deterministic FAQ scenario reports before/after costs of **0.0275655 / 0.0018245 scenario USD**, 100/5 model calls, 0/95 exact-cache hits, and approximately **5.006 / 0.2 ms** p50 latency. Its **93.4% saving** is printed next to a **100% deterministic Golden verdict**. Prices, token estimates, cache discount and cache-hit latency are assumptions; they are not billed provider usage. The Golden verdict does not itself test the cached path.

The **65.9% prefix-cache ratio** is synthesized by `RuleBasedClient`. The exact-cache near-miss result is **0/5 key collisions**. No real provider cache-ratio proof or calibrated semantic-cache tier is captured. The cache is benchmark-only and its historical key omits a grounding/policy revision. See [BENCHMARKS.md](BENCHMARKS.md) for the full methodology and remaining economic evidence.

The scripted reliability drill captures two 429 failures followed by success and an outage followed by the open-weight fallback. The four-part demo captures a grounded answer, return action, refusal and fallback. These faults and demos use deterministic clients; the live provider comparison uses direct adapters and does not exercise real provider failover.

## Known limitations and submission classification

- **CRITICAL BEFORE SUBMISSION:** verify the final normal tests and safety suite, secret/history scan, latest-source integrity and no-key default; restart/run the final Colab notebook and review the retained compatibility warning. The rubric does not permit a red safety suite.
- **ALREADY SATISFIED:** all marginal Golden strata ≥8; Arabic-majority 56-case set; paired 32-attack/32-legitimate guard results; captured 100% high-risk safety; both live providers; deterministic regression, fault and four-part evidence.
- **DOCUMENTED LIMITATION:** live judge calibration, language-split model extraction/repair, provider-verified native tools, full live slices/costs, real prefix caching, measured semantic-cache threshold, complete attempt metering and measured self-host break-even. Finite guards and domain-specific grounding remain limited detectors.
- **NICE TO HAVE:** extra isolated stage demonstrations, more detailed per-case transcripts and optional course extensions. They cannot substitute for missing mandatory evidence.

[The rubric map](RUBRIC_MAP.md) ties each requirement to code and captured evidence without self-awarded points.
