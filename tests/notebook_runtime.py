"""Shared helpers for building a namespace from the notebook, addressed by cell id.

Cell ids are stable across insertions; positional indices are not.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Raqmi_Capstone.ipynb"

# Original definition cells, in notebook order. No Colab bootstrap, no live cells.
DEFINITION_CELL_IDS = (
    "59801e2a",   # imports and ENABLE_LIVE_BACKENDS
    "73eaacc4",   # prompt artefacts
    "c0a06911",   # catalogue, policy, orders
    "4b881e89",   # Pydantic schemas
    "5ee3c60d",   # session, tools, tool log
    "aaa94323",   # LLMClient boundary and adapters
    "f4441e3e",   # §7 guard wall
    "83e57831",   # router, extraction, ask()
)
GUARD_PIPELINE_CELL_ID = "raqmi-guard-pipeline"


def load_notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def cell_source(notebook: dict, cell_id: str) -> str:
    for cell in notebook["cells"]:
        if cell["id"] == cell_id:
            return "".join(cell["source"])
    raise AssertionError(f"Notebook has no cell {cell_id}")


def build_namespace(cell_ids=DEFINITION_CELL_IDS, module_name="_raqmi_cell_runtime"):
    """Execute the named cells into a fresh module namespace, quietly."""
    notebook = load_notebook()
    module = ModuleType(module_name)
    sys.modules[module_name] = module
    with contextlib.redirect_stdout(io.StringIO()):
        for cell_id in cell_ids:
            code = cell_source(notebook, cell_id)
            exec(compile(code, f"notebook-cell-{cell_id}", "exec"), module.__dict__)
    return module.__dict__
