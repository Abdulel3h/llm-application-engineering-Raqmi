# Source provenance

The standalone uploaded notebook is the source of truth. No old notebook or model weights are included in this repository.

| Inspected input | Local modification time (Asia/Riyadh) | Finding |
|---|---|---|
| `Raqmi_Capstone_ALLaM_vLLM_FIXED.ipynb` | 2026-09-09 16:12:24 | Latest, 132,016 bytes, 55 cells, both providers' live outputs. |
| `Raqmi_ALLaM_vLLM_FIXED_Pack.zip` | 2026-09-09 13:05:38 | Two files: older 113,315-byte notebook and `README_FIX.txt`; no final live capture. |
| Extracted FIXED notebook | 2026-09-09 13:05:59 | Byte-identical to the notebook in the FIXED ZIP. |
| `Raqmi_ALLaM_vLLM_Colab_Pack.zip` | 2026-09-09 11:47:10 | Earlier notebook and README; lacks the later CUDA compatibility repair. |

Latest original notebook SHA-256:

```text
d02e4cb4a4e3a6dac19750d064157abf8b6f7ea0f5ae519acbe1891ac58268a0
```

Older FIXED notebook SHA-256:

```text
2e7df246f85aa9322268651f712c4fb9482247bb7017bf1b76bfb3c81821810e
```

The latest and older FIXED sources differ only in the original comparison flag (`False` → `True`). The latest additionally contains the readiness, compatibility, provider binding, smoke test, diagnostic, and final live comparison outputs. The short `README_FIX.txt` describes the TorchAudio/CUDA repair; it is supporting context, not a separate instruction or evidence of a rerun.

## Finalization changes

The canonical filename is now `Raqmi_Capstone.ipynb`. All original cell IDs, captured output objects, and execution counts are retained. The live comparison was executed as count 27 after the four-part demo (count 26), so its position is not evidence of a single fresh top-to-bottom live run.

Only three original code cells changed, solely to provide explicit live opt-in:

| Cell ID / section | Change |
|---|---|
| `59801e2a` / 0 Setup | Add `ENABLE_LIVE_BACKENDS = False`. |
| `d1f953e3` / 6A | Skip secret access, GPU detection, and endpoint readiness checks when live mode is disabled. |
| `238a9f1b` / 16 | Derive `RUN_LIVE_GOLDEN` from the explicit live flag. |

Application handlers, provider logic, prompts, Golden Set, attack corpus, legitimate corpus, labels, and thresholds are unchanged. Narrative cells now distinguish direct tool dispatch, synthetic judge/cache/demo evidence, captured results, and remaining submission work. Their old unchecked checklist and stale adapter instructions were replaced with actual status.

The independent optional native-tool module was added after capture. Historical live scores do not validate that module. Local tests do not recreate a GPU or paid provider run.

[The source manifest](evidence/source_manifest.json) records original and finalized cell-source digests, output digests, and execution counts. The local validator checks them. This manifest is an integrity record tied to the supplied artifact, not a cryptographic attestation by the providers.

## Repository history

The target GitHub repository had no commits when inspected and cloned. Finalization commits are contemporary, logical additions; they do not claim to reconstruct the trainee's earlier development history or use invented dates. Original uploads remain untouched outside the repository.
