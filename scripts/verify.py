"""Run the project's quality gates and emit a structured report.

Single source of truth for "is the build green?". Three checks run in sequence:
ruff format --check, ruff check, mypy, pytest. Results are aggregated to
.build/verify_report.json and the script exits with the worst child code.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / ".build"
REPORT_PATH = BUILD_DIR / "verify_report.json"


def run(name: str, argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return {
        "name": name,
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "argv": argv,
    }


def parse_mypy_errors(stdout: str) -> list[dict[str, Any]]:
    pat = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?:\d+:)?\s*(?P<kind>error|note):\s*(?P<msg>.+)$"
    )
    errors: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        m = pat.match(line.strip())
        if m and m.group("kind") == "error":
            errors.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "msg": m.group("msg"),
                }
            )
    return errors


def parse_pytest_failures(stdout: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    pat = re.compile(r"^FAILED\s+(?P<nodeid>\S+)(?:\s+-\s+(?P<msg>.*))?$")
    for line in stdout.splitlines():
        m = pat.match(line.strip())
        if m:
            failures.append({"nodeid": m.group("nodeid"), "msg": m.group("msg") or ""})
    return failures


def parse_ruff_issues(stdout: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pat = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<code>\S+)\s*(?P<msg>.+)$")
    for line in stdout.splitlines():
        m = pat.match(line.strip())
        if m:
            issues.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "code": m.group("code"),
                    "msg": m.group("msg"),
                }
            )
    return issues


def main() -> int:
    BUILD_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    checks: dict[str, dict[str, Any]] = {}
    checks["ruff_format"] = run("ruff_format", ["uv", "run", "ruff", "format", "--check", "."])
    checks["ruff_lint"] = run("ruff_lint", ["uv", "run", "ruff", "check", "."])
    checks["mypy"] = run("mypy", ["uv", "run", "mypy", "src/deep_sound"])
    checks["pytest"] = run("pytest", ["uv", "run", "pytest", "-q"])

    # Structured detail
    if checks["ruff_lint"]["status"] == "fail":
        checks["ruff_lint"]["issues"] = parse_ruff_issues(checks["ruff_lint"]["stdout"])
    if checks["mypy"]["status"] == "fail":
        checks["mypy"]["issues"] = parse_mypy_errors(checks["mypy"]["stdout"])
    if checks["pytest"]["status"] == "fail":
        checks["pytest"]["failures"] = parse_pytest_failures(checks["pytest"]["stdout"])

    overall = "pass" if all(c["status"] == "pass" for c in checks.values()) else "fail"
    worst_exit = max(c["exit_code"] for c in checks.values())

    report = {
        "timestamp": timestamp,
        "overall": overall,
        "checks": checks,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))

    # One-line summary to stdout
    print(f"verify: {overall}")
    for name, c in checks.items():
        marker = "OK" if c["status"] == "pass" else "FAIL"
        print(f"  [{marker}] {name} (exit={c['exit_code']})")
    print(f"report: {REPORT_PATH.relative_to(REPO_ROOT)}")

    return 0 if overall == "pass" else worst_exit


if __name__ == "__main__":
    sys.exit(main())
