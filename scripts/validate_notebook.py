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
ORIGINAL_NOTEBOOK_SHA256 = "3f4bf6ff4bc2ef2f94b1fe88abbc77bf442d5a604a15c16734a33664b228d0d3"
ORIGINAL_OUTPUT_SHA256 = "9b0a7d9bd8030d25f14364dbb2d527bf9f068da71a8281ff11fc17072e94055e"
EXPECTED_LIVE = {
    "commercial": {
        "mode": "LIVE",
        "model": "deepseek-v4-flash",
        "quality": 0.8928571428571429,
        "arabic": 0.8620689655172413,
        "safety": 1.0,
        "wall_s": 67.33267155800013,
    },
    "open_weight": {
        "mode": "LIVE",
        "model": "humain-ai/ALLaM-7B-Instruct-preview",
        "quality": 0.8928571428571429,
        "arabic": 0.896551724137931,
        "safety": 1.0,
        "wall_s": 60.25017996800011,
    },
}


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def captured_output_hash(notebook):
    return canonical_hash([
        {"index": i, "outputs": cell.get("outputs", []),
         "execution_count": cell.get("execution_count")}
        for i, cell in enumerate(notebook["cells"])
        if cell["cell_type"] == "code"
    ])


def captured_live(notebook):
    """Read recorded JSON; never substitute freshly generated demo metrics."""
    text = "".join(
        "".join(output.get("text", []))
        for output in notebook["cells"][44].get("outputs", [])
        if output.get("output_type") == "stream"
    )
    if "LIVE BACKEND COMPARISON: CAPTURED" not in text:
        raise AssertionError("Saved LIVE comparison marker is missing")
    comparison, _ = json.JSONDecoder().raw_decode(text.lstrip())
    if comparison != EXPECTED_LIVE:
        raise AssertionError("Saved LIVE comparison differs from the uploaded evidence")
    return comparison


def verify_saved_evidence(notebook):
    if captured_output_hash(notebook) != ORIGINAL_OUTPUT_SHA256:
        raise AssertionError("Saved cell outputs/execution counts changed from the uploaded notebook")
    manifest = json.loads((ROOT / "evidence/source_manifest.json").read_text(encoding="utf-8"))
    if manifest["source_sha256"] != ORIGINAL_NOTEBOOK_SHA256:
        raise AssertionError("Manifest does not identify the latest supplied source")
    if len(notebook["cells"]) != len(manifest["original_cells"]):
        raise AssertionError("Cell inventory differs from provenance manifest")
    for cell, record in zip(notebook["cells"], manifest["original_cells"]):
        if (cell["id"], cell["cell_type"]) != (record["id"], record["cell_type"]):
            raise AssertionError("Cell identity or order changed")
        if canonical_hash(cell["source"]) != record["final_source_sha256"]:
            raise AssertionError(f"Undocumented source change in cell {cell['id']}")
        if canonical_hash(cell.get("outputs", [])) != record["outputs_sha256"]:
            raise AssertionError("An original output was changed")
        if cell.get("execution_count") != record["execution_count"]:
            raise AssertionError("An original execution count was changed")
        if cell["id"] == manifest["golden_cell_id"] and canonical_hash(cell["source"]) != record["source_sha256"]:
            raise AssertionError("Latest supplied Golden Set or expectations were modified")
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
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            for node in ast.walk(ast.parse(source)):
                imports = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                           else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                if cell["id"] != "aaa94323" and any(name.split(".")[0] in {"openai", "anthropic", "deepseek"} for name in imports):
                    raise AssertionError(f"Provider SDK import outside adapter cell: {cell['id']}")
            compiled.append((index, compile(source, f"{path.name}:cell-{index}", "exec")))

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
        raise AssertionError("Notebook must default ENABLE_LIVE_BACKENDS to False")
    if namespace.get("RUN_LIVE_GOLDEN") is not False:
        raise AssertionError("Offline run unexpectedly enabled LIVE evaluation")
    if any(value["mode"] != "DEMO_PREVIEW" for value in namespace["comparison"].values()):
        raise AssertionError("Fresh offline results must be labeled DEMO_PREVIEW")
    if path.read_bytes() != before:
        raise AssertionError("Offline execution modified the saved notebook")
    return {
        "namespace": namespace,
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
    print(f"Deterministic Golden Set: {len(ns['GOLDEN'])} cases; "
          f"overall={ns['primary_report']['overall']:.2%}; safety={ns['primary_report']['safety']:.2%}")
    print(f"Guard suite: {ns['attack_blocked']}/{len(ns['ATTACKS'])} attacks blocked; "
          f"{ns['legit_blocked']}/{len(ns['LEGIT'])} legitimate prompts blocked")
    print("Saved LIVE comparison and all original outputs: unchanged; LIVE providers were NOT rerun")
    print("Network/process operations: blocked; notebook files: not written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
