# Rubric map

Every row points to the notebook section, the file, and the exact captured evidence, so nothing has to be hunted for. All evidence is in the official executed notebook [`Raqmi_Capstone.ipynb`](Raqmi_Capstone.ipynb) (SHA-256 `cffa505e0d2289f1654651d79b36b5edc55fe54b3d25003bd88fafea9c6eb345`), 87 cells, 47/47 code cells executed sequentially against live DeepSeek and live ALLaM/vLLM.

**Status vocabulary:** *LIVE* = measured against a real provider in that run. *Deterministic* = reproducible no-key result. *Scenario* = arithmetic over stated assumptions, not billing.

## 1 — Architecture and model boundary

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Router-first architecture, ADRs | §1 | cell `1aaaa06c`, [DECISIONS.md](DECISIONS.md) | four stable intents, documented trade-offs | Deterministic |
| Single model boundary | §6 | `LLMClient`, cell `aaa94323` | one abstraction; provider imports confined to the adapter; boundary assert `fe9245fe` | Deterministic |
| Commercial backend | §6A | cell `d1f953e3`, `a1c2778f` | `deepseek-v4-flash` bound and used | **LIVE** |
| Open-weight backend, local serving | §6A | vLLM on Colab T4 | `humain-ai/ALLaM-7B-Instruct-preview`, OpenAI-compatible endpoint `http://127.0.0.1:8000/v1`; `ALLaM/vLLM READY`; smoke test `4d49188f` | **LIVE** |
| Deterministic routing policy | §8 | cell `83e57831` | model label corrected on evidence; unowned order always reaches the ownership check | Deterministic |
| Reliability and fallback | §17 | cell `969a5bf1` | scripted 429 → retry → success; outage → open-weight fallback | Deterministic |

## 2 — Structured output and tools

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Validated domain object | §4 | `ReturnRequest`, cell `4b881e89` | constrained order id, product, reason, language | Deterministic |
| Model extraction, validate → retry → repair → escalate | Live Structured Output Evaluation | `raqmi-structured-corpus`, `-pipeline`, `-report` | 20 cases, 10 per language, DeepSeek, 23.79 s | **LIVE** |
| Per-language pass rates | same | `raqmi-structured-report` | each language **5 first-pass valid, 1 after repair, 4 escalated**, 10/10 designed outcomes matched, safety invariants PASS | **LIVE** |
| Three tool risk classes | §5 | cell `5ee3c60d` | `lookup_order` read-only, `create_return` side-effecting, `escalate_to_human` terminal | Deterministic |
| Native model-issued tool calling | §9A | `raqmi-tools-module`, [raqmi_tool_calling.py](raqmi_tool_calling.py), [TOOL_CALLING.md](TOOL_CALLING.md) | `tool_calls` → envelope normalization → whitelist → strict Pydantic → canonicalization → authorization → execution → `role: tool` → final answer | **LIVE** |
| Authorized lookup | Native Tool Calling — Live Evidence | `raqmi-tools-live` | model issued `lookup_order`; executed; tool result returned | **LIVE** |
| Cross-user lookup denied | same | `raqmi-tools-live` | `authorization_denied`; no other customer's data exposed | **LIVE** |
| Authorized return | same | `raqmi-tools-live` | **`returns_created = 1`**, **`return_id = R-1001`**, canonical product `headphones` | **LIVE** |
| Negative and bounds assertions | §9A offline | `raqmi-tools-offline`, `raqmi-tools-negative` | unknown tool, malformed arguments, cross-user return, duplicate replay, iteration and tool-call limits, terminal tool | Deterministic |
| Authorization outside the LLM | §5, §9A | `Session.authorize_order()` | model cannot supply identity, ownership, membership or a return id | Deterministic |
| Risk-class and iteration logging | §9A | `NATIVE_TOOL_LOG` | every call logs tool, risk class, iteration, outcome, product canonicalization | **LIVE** |

## 3 — Prompts and guardrails

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Versioned prompt artefacts, changelog | §2 | cell `73eaacc4` | central registry; no inline handler prompts; served version logged | Deterministic |
| Five stages demonstrated separately | §7A | `raqmi-guard-stage1` … `stage5`, [GUARDRAILS.md](GUARDRAILS.md) | one cell per stage: normalization, deterministic guard, PII masking, safety classifier, outbound wall | Deterministic |
| Attack corpus ≥30, ≥95% blocked | §10 | cell `52ef9833` | **32/32 = 100%** | Deterministic |
| Legitimate corpus ≥30, 0% false positives | §10 | cell `52ef9833` | **0/32 = 0%** | Deterministic |
| Whole-wall re-measurement | §10A | `raqmi-guard-eval` | same 100% / 0% under all five stages | Deterministic |
| No regression from the wall | §12B | `raqmi-guard-parity` | 0 of 56 Golden answers changed | Deterministic |
| PII masking, outbound leakage | §7A | `stage_mask_pii`, `stage_output_guard` | Arabic and English mobile/e-mail masking; canary, PII, internal-error and instruction-relay categories | Deterministic |

## 4 — Dataset, harness, judge

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| ≥40 cases, Arabic-majority, strata ≥8 | §11 | cell `31d0b2a6` | **56 cases**; ar 29 / en 27; intents 14/13/12/9/8; difficulty 12/16/28; risk 11/21/24 | Deterministic |
| Harness runs the real pipeline | §12 | cell `cf88d2d3` | `run_golden()` calls `ask()`; deterministic 56/56, high-risk 24/24 | Deterministic |
| Failed-case diagnosis | §12A | `raqmi-failed-cases` | every failure printed with criteria, guard category, router label and policy decision; high-risk failures listed separately | **LIVE** |
| Safety 100% | §16 | cell `238a9f1b` | DeepSeek 24/24, ALLaM 24/24 | **LIVE** |
| Slice-based regression gate | §14 | cell `2a6b7cbc` | clean PASS, seeded degraded prompt BLOCK | Deterministic |
| Calibrated LLM judge, κ ≥ 0.6 | Live LLM-as-a-Judge Calibration | `raqmi-judge-corpus`, `-run`, `-report` | **n = 36, agreement 0.778, κ 0.667**, target met, 8 disagreements printed, labels frozen by SHA-256, judge never sees them | **LIVE** |
| Judge is not the gate | same | `JUDGE_IS_REGRESSION_GATE = False` | §14 stays deterministic | Deterministic |
| Deterministic scaffold kept separate | §13 | cell `b4666e9b` | labelled DETERMINISTIC / SYNTHETIC; κ = 1.00 is plumbing only | Deterministic |

## 5 — Metering, caching, optimization

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Metering of model calls | §8 | `MODEL_CALL_LOG` | usage and latency recorded through the boundary | Deterministic |
| Cache design and near-miss safety | §15 | cells `ff8a50e3`, `4aed2e17` | exact key over model, prompt version, normalized text, language, params; **0/5** near-miss collisions | Deterministic |
| Prefix-cache accounting | §15 | cell `e61f8b9e` | **65.9%** simulated ratio | Scenario |
| Before/after saving with an evaluation verdict | §15 | cell `ff8a50e3` | 100 → 5 model calls, 95 cache hits, **93.4%** scenario saving beside a 100% Golden verdict | Scenario |

## 6 — Model comparison

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Same Golden Set on both providers | §16 | cell `238a9f1b`, [BENCHMARKS.md](BENCHMARKS.md) | DeepSeek and ALLaM, both `mode: LIVE` | **LIVE** |
| Quality, Arabic and safety slices | §16 | same | both **91.07%** overall, **89.66%** Arabic, **100%** high-risk | **LIVE** |
| Latency | §16 | same | DeepSeek **60.95 s**, ALLaM **63.91 s** sequential | **LIVE** |
| Routing recommendation | §21 | [DECISIONS.md](DECISIONS.md) | conditional on observed quality and wall time only | Deterministic |

## 7 — Complete application and submission

| Criterion | Notebook | File / cell | Evidence | Status |
|---|---|---|---|---|
| Colab Run all, bilingual conversation | whole notebook | counts 1–47, no gaps | one sequential live run | **LIVE** |
| Four-part demo | §18 | cell `fa8d1fac` | grounded answer, tool action, refused attack, graceful fallback — **FOUR-PART DEMO: PASS** | Deterministic |
| Runtime readiness check | Final submission check | `raqmi-final-check` | all ten checks PASS from live variables; **FINAL SUBMISSION READINESS: PASS** | **LIVE** |
| Documentation and provenance | — | [README](README.md), [EVALUATION_REPORT](EVALUATION_REPORT.md), [BENCHMARKS](BENCHMARKS.md), [TOOL_CALLING](TOOL_CALLING.md), [GUARDRAILS](GUARDRAILS.md), [SOURCE_PROVENANCE](SOURCE_PROVENANCE.md), `evidence/source_manifest.json` | every cell pinned by digest; validator refuses drift | Deterministic |
| No secrets | — | `scripts/scan_secrets.py` | 0 findings across tracked files and reachable git blobs | Deterministic |

## Not claimed

Provider billing or measured cache economics; saturated throughput or self-host break-even; a calibrated semantic-cache tier; complete live per-case export beyond the printed failed-case report; complete attempt metering; **ALLaM's own native tool-call parsing**; a second-annotator study for the judge corpus. Grounding, catalogue scope and PII coverage are intentionally narrow, and the lexical safety classifier is not a semantic model. Five FAQ cases failed per provider in the live run and are listed in [BENCHMARKS.md](BENCHMARKS.md).
