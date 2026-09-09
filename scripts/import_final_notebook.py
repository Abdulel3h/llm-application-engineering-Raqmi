"""Adopt the owner's final executed Colab notebook as the official submission.

The executed notebook is copied verbatim to ``Raqmi_Capstone.ipynb`` and every
cell is pinned in ``evidence/source_manifest.json``. Nothing is regenerated,
cleared or recomputed here: the outputs in the official notebook are exactly the
ones Google Colab produced during the owner's live run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "Raqmi_Capstone.ipynb"
MANIFEST = ROOT / "evidence" / "source_manifest.json"
GOLDEN_CELL_ID = "31d0b2a6"
LIVE_COMPARISON_CELL_ID = "238a9f1b"


def canonical_hash(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cell_text(cell) -> str:
    return "".join("".join(output.get("text", [])) for output in cell.get("outputs", []))


def build_manifest(notebook: dict, source_name: str, source_sha256: str) -> dict:
    records = [
        {
            "id": cell["id"],
            "cell_type": cell["cell_type"],
            "source_sha256": canonical_hash(cell["source"]),
            "outputs_sha256": canonical_hash(cell.get("outputs", [])),
            "execution_count": cell.get("execution_count"),
        }
        for cell in notebook["cells"]
    ]
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    comparison_cell = next(cell for cell in notebook["cells"]
                           if cell["id"] == LIVE_COMPARISON_CELL_ID)
    comparison, _ = json.JSONDecoder().raw_decode(cell_text(comparison_cell).lstrip())
    return {
        "official_notebook": OFFICIAL.name,
        "uploaded_filename": source_name,
        "uploaded_sha256": source_sha256,
        "capture": (
            "Final executed Google Colab run supplied by the owner: one sequential "
            "Run all, execution counts 1-47 with no gaps, live DeepSeek and live "
            "ALLaM served by vLLM on a Tesla T4. Every output in the official "
            "notebook was produced by Colab during that run and is copied verbatim; "
            "nothing here is generated locally."
        ),
        "digest_format": (
            "sha256 of UTF-8 json.dumps(value, ensure_ascii=False, sort_keys=True, "
            "separators=(comma, colon))"
        ),
        "golden_cell_id": GOLDEN_CELL_ID,
        "live_comparison_cell_id": LIVE_COMPARISON_CELL_ID,
        "cells_total": len(notebook["cells"]),
        "code_cells_total": len(code_cells),
        "code_cells_executed": sum(cell.get("execution_count") is not None
                                   for cell in code_cells),
        "captured_live_comparison": comparison,
        "cells": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executed", type=Path,
                        help="The owner's final executed notebook.")
    args = parser.parse_args()

    raw = args.executed.read_bytes()
    notebook = json.loads(raw.decode("utf-8"))
    if notebook.get("nbformat") != 4:
        raise SystemExit("expected a format-4 notebook")
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    unexecuted = [cell["id"] for cell in code_cells if cell.get("execution_count") is None]
    if unexecuted:
        raise SystemExit(f"refusing an unexecuted notebook; cells without output: {unexecuted}")

    OFFICIAL.write_bytes(raw)
    manifest = build_manifest(notebook, args.executed.name,
                              hashlib.sha256(raw).hexdigest())
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    print(f"official notebook : {OFFICIAL.name}")
    print(f"sha256            : {hashlib.sha256(OFFICIAL.read_bytes()).hexdigest()}")
    print(f"cells             : {manifest['cells_total']} "
          f"({manifest['code_cells_executed']}/{manifest['code_cells_total']} code cells executed)")
    print(f"live comparison   : {json.dumps(manifest['captured_live_comparison'])[:120]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
