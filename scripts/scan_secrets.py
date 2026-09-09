"""Scan project files and reachable Git blobs; never print matched values.

This is a conservative local credential-pattern check, not a guarantee that every
possible secret can be recognized. Names such as DEEPSEEK_API_KEY are not secrets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "provider_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "huggingface_token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "bearer_literal": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}"),
    "credential_url": re.compile(r"https?://[^\s/@:]+:[^\s/@]+@"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\b"),
    "literal_credential": re.compile(
        r"(?i)[\"']?(?:[A-Z_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD|CLIENT_SECRET))"
        r"[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_./+=-]{16,})[\"']"
    ),
}
SUSPICIOUS_NAMES = {".env", ".bash_history", ".python_history", ".zsh_history", "credentials.json"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}


def findings(label: str, data: bytes) -> list[dict]:
    text = data.decode("utf-8", "replace")
    # Notebook JSON strings escape quotes; inspect decoded cells/outputs/metadata too.
    if label.endswith(".ipynb"):
        try:
            text += "\n" + flatten(json.loads(text))
        except ValueError:
            pass
    return [
        {"location": label, "rule": name, "line": text.count("\n", 0, match.start()) + 1}
        for name, pattern in PATTERNS.items() for match in pattern.finditer(text)
    ]


def flatten(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(flatten(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(str(key) + "\n" + flatten(item) for key, item in value.items())
    return str(value)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL)


def scan(history: bool = True) -> dict:
    issues = []
    file_count = blob_count = 0
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in SKIP_DIRS for part in relative.parts):
            continue
        file_count += 1
        if path.name in SUSPICIOUS_NAMES or path.name.startswith(".env.") or path.suffix == ".key":
            issues.append({"location": relative.as_posix(), "rule": "sensitive_filename"})
        issues.extend(findings(relative.as_posix(), path.read_bytes()))
    if history:
        try:
            objects = git("rev-list", "--objects", "--all", "--reflog").decode().splitlines()
        except subprocess.CalledProcessError:
            objects = []  # Empty repository has no history to scan.
        seen = set()
        for entry in objects:
            oid, _, filename = entry.partition(" ")
            if oid in seen or git("cat-file", "-t", oid).strip() != b"blob":
                continue
            seen.add(oid)
            blob_count += 1
            issues.extend(findings(f"git:{oid}:{filename}", git("cat-file", "blob", oid)))
    return {"files_scanned": file_count, "git_blobs_scanned": blob_count,
            "findings": issues, "status": "FAIL" if issues else "PASS"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()
    result = scan(history=not args.no_history)
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["findings"]))
