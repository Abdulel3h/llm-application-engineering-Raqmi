# Source provenance

## The official notebook

`Raqmi_Capstone.ipynb` is the owner's **final executed Google Colab run**, copied into this repository byte for byte.

```text
SHA-256  cffa505e0d2289f1654651d79b36b5edc55fe54b3d25003bd88fafea9c6eb345
cells    87 (47 code, 40 markdown)
executed 47/47 code cells, execution counts 1-47 with no gaps
uploaded Raqmi_Capstone_FINAL_CANDIDATE(2).ipynb
```

**Every output in it was produced by Google Colab during that live run.** Nothing was generated, regenerated, edited or recomputed locally. The run used live DeepSeek (`deepseek-v4-flash`) and live ALLaM (`humain-ai/ALLaM-7B-Instruct-preview`) served by vLLM on a Tesla T4, and its final cell reports `FINAL SUBMISSION READINESS: PASS`.

`scripts/import_final_notebook.py` performed the adoption: it refuses a notebook with any unexecuted code cell, copies the bytes unchanged, and writes `evidence/source_manifest.json` pinning every cell's source digest, output digest and execution count.

## Integrity checking

`scripts/validate_notebook.py` re-verifies on every run that:

- every cell matches the manifest's source, output and execution-count digests;
- no code cell is unexecuted, and the counts form one sequential 1–47 run;
- the Golden Set cell source is unchanged;
- the live markers the documentation cites are present in saved output — the backend comparison JSON, `LIVE STRUCTURED OUTPUT EVALUATION: CAPTURED`, the judge's `n = 36 / agreement = 0.778 / Cohen kappa = 0.667`, the native `returns_created: 1` and `return_id: R-1001`, `guard suite: PASS`, `FOUR-PART DEMO: PASS` and `FINAL SUBMISSION READINESS: PASS`.

Editing a captured number, stripping an output or altering the Golden Set makes validation fail. Offline validation compiles a no-key copy of the setup cell **in memory** and confirms afterwards that the file on disk is untouched.

## How this artifact was reached

The notebook evolved through several owner-executed Colab runs. Each superseded the last; only the final one is evidence. The chain, for transparency:

| Stage | Outcome |
|---|---|
| Earlier 55-cell captures | Original 56-case Golden Set and first live DeepSeek/ALLaM comparison. |
| Post-capture additions | Native tool calling, five-stage guardrail pipeline, live structured-output evaluation and live judge calibration were added as new sections. |
| Executed run (85 cells) | Exposed two defects: every native tool call was refused because the envelope model forbade the provider's `index` field, and DeepSeek high-risk safety measured 0.958 because ownership was only checked when the router happened to route correctly. |
| Executed run (85 cells, after those fixes) | Both defects closed; safety 24/24 for both providers. Exposed the last defect: a native return was denied because the model emitted `Headphones` while the order stored `headphones`. |
| **Final executed run (87 cells)** | Catalogue-controlled product canonicalization added; the authorized native return now completes live with `returns_created = 1`. **This is the official notebook.** |

Earlier measurements are **superseded** and are not quoted anywhere as current results. Where a document mentions one, it is labelled as history.

## Local additions alongside the notebook

The notebook is self-contained for Colab: the native tool-calling module is embedded in cell `raqmi-tools-module`. The repository also carries `raqmi_tool_calling.py` as the reviewable copy of that same code; `scripts/sync_tool_module.py --check` fails if the two ever drift, and a test enforces the same equality.

Everything else in the repository — tests, validator, secret scanner, documentation — is local tooling. It uses deterministic and scripted providers and never re-runs a real provider or a GPU, so it can confirm the captured evidence is intact but cannot create it.

## Repository history

The repository is built from small, logical commits recording this finalization work. It does not invent earlier development dates and does not claim that the executed notebook was produced by those commits: the notebook came from Google Colab, and the commits record its adoption and the surrounding tooling.
