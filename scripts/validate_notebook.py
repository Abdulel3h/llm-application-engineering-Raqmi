"""Compile and execute Raqmi's offline notebook without modifying saved evidence.

Requires Python 3.10+ and Pydantic 2. No package installation, external requests,
GPU processes, or notebook writes are performed. The network/process guard is a
regression tripwire for this reviewed notebook, not an untrusted-code sandbox.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType
from unittest import mock
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Raqmi_Capstone.ipynb"
# The official notebook is the owner's final executed Colab run, copied verbatim.
OFFICIAL_NOTEBOOK_SHA256 = "cffa505e0d2289f1654651d79b36b5edc55fe54b3d25003bd88fafea9c6eb345"
LIVE_COMPARISON_CELL_ID = "238a9f1b"
SETUP_CELL_ID = "59801e2a"
FINAL_CHECK_CELL_ID = "raqmi-final-check"
LIVE_FLAG_ON = "ENABLE_LIVE_BACKENDS = True"
LIVE_FLAG_OFF = "ENABLE_LIVE_BACKENDS = False"

# Captured LIVE measurements, checked independently of all fresh offline metrics.
EXPECTED_LIVE = {
    "commercial": {
        "mode": "LIVE",
        "model": "deepseek-v4-flash",
        "quality": 0.9107142857142857,
        "arabic": 0.896551724137931,
        "safety": 1.0,
        "wall_s": 60.947293607000006,
    },
    "open_weight": {
        "mode": "LIVE",
        "model": "humain-ai/ALLaM-7B-Instruct-preview",
        "quality": 0.9107142857142857,
        "arabic": 0.896551724137931,
        "safety": 1.0,
        "wall_s": 63.910626944,
    },
}

# Markers the submission's documentation cites, checked against saved output.
EXPECTED_CAPTURES = {
    "raqmi-structured-report": (
        "mode: LIVE | model: deepseek-v4-flash",
        "LIVE STRUCTURED OUTPUT EVALUATION: CAPTURED",
        "structured-output safety invariants: PASS",
        "Cases: 10", "First-pass valid: 5/10", "After repair: 1/10", "Escalated: 4/10",
    ),
    "raqmi-judge-report": (
        "[LIVE] judge=deepseek-v4-flash", "n = 36", "agreement = 0.778",
        "Cohen kappa = 0.667", "target kappa >= 0.60 -> MET",
        "used as a regression gate: False",
    ),
    "raqmi-tools-live": (
        "LIVE NATIVE TOOL CALLING: CAPTURED",
        '"returns_created": 1', '"return_id": "R-1001"',
        '"product_canonical": "headphones"',
        "authorization_denied",
        "tool-call diagnostics: none recorded",
    ),
    "raqmi-final-check": ("FINAL SUBMISSION READINESS: PASS",),
    "52ef9833": (
        "attacks: 32/32 blocked = 100.0%",
        "legitimate: 0/32 blocked = false-positive 0.0%",
        "guard suite: PASS",
    ),
    "fa8d1fac": ("FOUR-PART DEMO: PASS",),
}


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_manifest():
    return json.loads((ROOT / "evidence/source_manifest.json").read_text(encoding="utf-8"))


def cell_by_id(notebook, cell_id):
    for cell in notebook["cells"]:
        if cell["id"] == cell_id:
            return cell
    raise AssertionError(f"Cell {cell_id} is missing from the notebook")


def captured_live(notebook):
    """Validate the saved LIVE comparison, never a freshly generated demo score."""
    cell = cell_by_id(notebook, LIVE_COMPARISON_CELL_ID)
    text = "".join("".join(output.get("text", []))
                   for output in cell.get("outputs", [])
                   if output.get("output_type") == "stream")
    if "LIVE BACKEND COMPARISON: CAPTURED" not in text:
        raise AssertionError("Saved LIVE comparison marker is missing")
    comparison, _ = json.JSONDecoder().raw_decode(text.lstrip())
    if comparison != EXPECTED_LIVE:
        raise AssertionError("Saved LIVE comparison differs from the captured Colab run")
    return comparison


def verify_saved_evidence(notebook):
    """The official notebook must still be the owner's executed Colab artifact.

    Every cell is pinned by the manifest, every code cell must carry the
    execution count from that sequential run, and the live markers that make the
    submission's claims must still be present in the saved output. Nothing here
    regenerates evidence; it only refuses a notebook that has drifted from the
    capture.
    """
    manifest = load_manifest()
    records = {record["id"]: record for record in manifest["cells"]}
    if len(records) != len(manifest["cells"]):
        raise AssertionError("Provenance manifest has duplicate cell ids")
    if [cell["id"] for cell in notebook["cells"]] != [r["id"] for r in manifest["cells"]]:
        raise AssertionError("Notebook cells differ from the provenance manifest")

    executed = 0
    for cell in notebook["cells"]:
        record = records[cell["id"]]
        if cell["cell_type"] != record["cell_type"]:
            raise AssertionError(f"Cell type changed for {cell['id']}")
        if canonical_hash(cell["source"]) != record["source_sha256"]:
            raise AssertionError(f"Source changed in cell {cell['id']}")
        if canonical_hash(cell.get("outputs", [])) != record["outputs_sha256"]:
            raise AssertionError(f"Captured output changed in cell {cell['id']}")
        if cell.get("execution_count") != record["execution_count"]:
            raise AssertionError(f"Execution count changed in cell {cell['id']}")
        if cell["cell_type"] == "code":
            if cell.get("execution_count") is None:
                raise AssertionError(f"Official notebook has an unexecuted cell: {cell['id']}")
            executed += 1
    if executed != manifest["code_cells_executed"]:
        raise AssertionError("Executed code-cell count differs from the manifest")

    golden = cell_by_id(notebook, manifest["golden_cell_id"])
    if canonical_hash(golden["source"]) != records[manifest["golden_cell_id"]]["source_sha256"]:
        raise AssertionError("The Golden Set or its expectations were modified")

    # The exact live markers this submission's documentation relies on.
    for cell_id, fragments in EXPECTED_CAPTURES.items():
        cell = cell_by_id(notebook, cell_id)
        output_text = "".join("".join(output.get("text", [])) for output in cell.get("outputs", []))
        missing = [fragment for fragment in fragments if fragment not in output_text]
        if missing:
            raise AssertionError(f"Captured LIVE evidence missing from {cell_id}: {missing}")
    return captured_live(notebook)


@contextlib.contextmanager
def offline_only():
    """Block network transports, DNS, and process launches, including swallowed attempts."""
    attempts = []

    def blocked(*args, **kwargs):
        # Do not include arguments: they might contain credentials or request bodies.
        attempts.append("network or process operation")
        raise RuntimeError("Offline validation forbids network and process operations")

    with contextlib.ExitStack() as stack:
        for target, attribute in (
            (socket, "create_connection"), (socket, "getaddrinfo"),
            (socket.socket, "connect"), (socket.socket, "connect_ex"),
            (socket.socket, "sendto"), (urllib.request, "urlopen"),
            (subprocess, "Popen"), (subprocess, "run"),
            (subprocess, "check_output"), (os, "system"), (os, "popen"),
        ):
            stack.enter_context(mock.patch.object(target, attribute, side_effect=blocked))
        yield
    if attempts:
        raise AssertionError(f"Offline validation intercepted {len(attempts)} forbidden operation(s)")


def run_notebook(path=NOTEBOOK):
    """Execute all cells in order with the checked-in offline configuration."""
    import pydantic

    if int(pydantic.__version__.split(".")[0]) != 2:
        raise RuntimeError("Offline validation requires Pydantic >=2,<3")
    path = Path(path)
    before = path.read_bytes()
    notebook = json.loads(before)
    if notebook.get("nbformat") != 4:
        raise AssertionError("Expected notebook format 4")
    saved_live = verify_saved_evidence(notebook)
    compiled = []
    forced_offline = False
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            for node in ast.walk(ast.parse(source)):
                imports = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                           else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                if cell["id"] != "aaa94323" and any(name.split(".")[0] in {"openai", "anthropic", "deepseek"} for name in imports):
                    raise AssertionError(f"Provider SDK import outside adapter cell: {cell['id']}")
            filename = f"{path.name}:cell-{cell['id']}"
            code = compile(source, filename, "exec")
            if cell["id"] == SETUP_CELL_ID:
                tree = ast.parse(source)
                assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                               and any(isinstance(target, ast.Name) and target.id == "ENABLE_LIVE_BACKENDS"
                                       for target in node.targets)]
                if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Constant):
                    raise AssertionError("Expected one literal live-backend setup switch")
                if assignments[0].value.value is True:
                    assignments[0].value = ast.Constant(value=False)
                    code = compile(ast.fix_missing_locations(tree), filename, "exec")
                    forced_offline = True
                elif assignments[0].value.value is not False:
                    raise AssertionError("Live-backend switch must be a boolean")
            compiled.append((index, code))

    # Register the namespace so dataclasses can resolve postponed annotations.
    module = ModuleType("_raqmi_offline_notebook")
    sys.modules[module.__name__] = module
    module.__dict__["__file__"] = str(path)
    stream = io.StringIO()
    with offline_only(), contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        for index, code in compiled:
            try:
                exec(code, module.__dict__)
            except Exception as exc:
                raise RuntimeError(f"Offline execution failed in zero-based code cell {index}") from exc
    namespace = module.__dict__
    if namespace.get("ENABLE_LIVE_BACKENDS") is not False:
        raise AssertionError("Offline execution must keep ENABLE_LIVE_BACKENDS=False")
    if namespace.get("RUN_LIVE_GOLDEN") is not False:
        raise AssertionError("Offline run unexpectedly enabled LIVE evaluation")
    if any(value["mode"] != "DEMO_PREVIEW" for value in namespace["comparison"].values()):
        raise AssertionError("Fresh offline results must be labeled DEMO_PREVIEW")
    for flag in ("RUN_LIVE_TOOL_EVAL", "RUN_LIVE_STRUCTURED_EVAL", "RUN_LIVE_JUDGE"):
        if namespace.get(flag) is not False:
            raise AssertionError(f"Offline run unexpectedly enabled {flag}")
    for section, key in (("LIVE_TOOL_EVIDENCE", "mode"), ("STRUCTURED_REPORT", "mode"),
                         ("JUDGE_CALIBRATION", "mode")):
        if namespace[section][key] == "LIVE":
            raise AssertionError(f"Offline run produced a LIVE label in {section}")
    if path.read_bytes() != before:
        raise AssertionError("Offline execution modified the saved notebook")
    return {
        "namespace": namespace,
        "forced_offline": forced_offline,
        "compiled_cells": [index for index, _ in compiled],
        "executed_cells": [index for index, _ in compiled],
        "captured_live": saved_live,
        "stdout": stream.getvalue(),
        "notebook_sha256": hashlib.sha256(before).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK)
    parser.add_argument("--verbose", action="store_true", help="Show deterministic cell output")
    args = parser.parse_args()
    result = run_notebook(args.notebook)
    ns = result["namespace"]
    if args.verbose:
        print(result["stdout"])
    print(f"OFFLINE PASS: {len(result['compiled_cells'])} code cells compiled and executed in order")
    if result["forced_offline"]:
        print("Notebook ships with ENABLE_LIVE_BACKENDS=True; validation compiled a "
              "no-key copy in memory and did not modify the file")
    print(f"Deterministic Golden Set: {len(ns['GOLDEN'])} cases; "
          f"overall={ns['primary_report']['overall']:.2%}; safety={ns['primary_report']['safety']:.2%}")
    print(f"Guard suite: {ns['attack_blocked']}/{len(ns['ATTACKS'])} attacks blocked; "
          f"{ns['legit_blocked']}/{len(ns['LEGIT'])} legitimate prompts blocked")
    print(f"Five-stage pipeline: {ns['pipeline_block_rate']:.0%} attack block; "
          f"{ns['pipeline_fp_rate']:.0%} false positives; Golden Set answers unchanged")
    print(f"Native tools: {len(ns['NATIVE_TOOL_LOG'])} logged calls across risk classes "
          f"{sorted({e['risk_class'] for e in ns['NATIVE_TOOL_LOG']})}")
    print(f"Structured output ({ns['STRUCTURED_REPORT']['mode']}): "
          f"ar {ns['STRUCTURED_REPORT']['ar']}; en {ns['STRUCTURED_REPORT']['en']}")
    print(f"Judge calibration ({ns['JUDGE_CALIBRATION']['mode']}): "
          f"n={ns['JUDGE_CALIBRATION']['final']['n']}, "
          f"kappa={ns['JUDGE_CALIBRATION']['final']['kappa']:.3f}")
    print("Captured LIVE evidence (backend comparison, structured output, judge, "
          "native tools, readiness): verified present and unchanged")
    print("Official notebook is the owner's executed Colab run; LIVE providers were NOT rerun here")
    print("Network/process operations: blocked; notebook files: not written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
