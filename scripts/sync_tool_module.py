"""Keep the notebook's native tool-calling cell byte-identical to raqmi_tool_calling.py.

The module file is the source of truth: it is what reviewers read and what the
test suite imports. The notebook carries a copy so that a standalone Colab upload
needs no second file. ``--check`` verifies; the default writes the notebook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Raqmi_Capstone.ipynb"
MODULE = ROOT / "raqmi_tool_calling.py"
CELL_ID = "raqmi-tools-module"


def module_source() -> str:
    """The cell text: the module without its trailing newline."""
    return MODULE.read_text(encoding="utf-8").rstrip("\n")


def notebook_cell(notebook: dict) -> dict:
    for cell in notebook["cells"]:
        if cell["id"] == CELL_ID:
            return cell
    raise SystemExit(f"Notebook has no cell {CELL_ID}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if the copies differ; write nothing.")
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK,
                        help="Candidate notebook to inspect or synchronize.")
    args = parser.parse_args()

    notebook = json.loads(args.notebook.read_text(encoding="utf-8"))
    cell = notebook_cell(notebook)
    wanted = module_source()
    current = "".join(cell["source"])
    if current == wanted:
        print(f"in sync: {MODULE.name} == notebook cell {CELL_ID}")
        return 0
    if args.check:
        print(f"OUT OF SYNC: {MODULE.name} differs from notebook cell {CELL_ID}.")
        print("Run: python scripts/sync_tool_module.py")
        return 1
    if cell.get("outputs") or cell.get("execution_count") is not None:
        raise SystemExit("Refusing to rewrite a cell that carries captured output")
    cell["source"] = wanted.splitlines(keepends=True)
    args.notebook.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    print(f"updated notebook cell {CELL_ID} from {MODULE.name}")
    print("Remember to refresh evidence/source_manifest.json if a hash check now fails.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
