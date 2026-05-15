"""Produce a focused repair brief from .build/verify_report.json.

Called by the Stop hook after a failed verify. The brief lists failing checks
with file:line context and a scope hint, then drops it at .build/repair_brief.md
for /repair to consume.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / ".build"
REPORT_PATH = BUILD_DIR / "verify_report.json"
BRIEF_PATH = BUILD_DIR / "repair_brief.md"
ATTEMPTS_PATH = BUILD_DIR / "repair_attempts.txt"
MAX_ATTEMPTS = 3


def attempts_so_far() -> int:
    if not ATTEMPTS_PATH.exists():
        return 0
    try:
        return int(ATTEMPTS_PATH.read_text().strip() or "0")
    except ValueError:
        return 0


def render_brief(report: dict[str, Any]) -> str:
    attempt = attempts_so_far() + 1  # this would be the next attempt
    lines = [
        f"# Repair brief — {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Attempt {attempt} of {MAX_ATTEMPTS}.",
        "",
        f"Overall: **{report.get('overall', 'unknown')}**",
        "",
        "## Failed checks",
    ]
    files_touched: set[str] = set()
    failed_names = [name for name, c in report["checks"].items() if c["status"] == "fail"]
    if not failed_names:
        lines.append("- (none — but overall is failing; inspect report manually)")
    else:
        for name in failed_names:
            c = report["checks"][name]
            count = (
                len(c.get("issues") or c.get("failures") or [])
                if c.get("issues") or c.get("failures")
                else "?"
            )
            lines.append(f"- {name}: exit={c['exit_code']} ({count} items)")

    lines.append("")
    lines.append("## Specific items")

    item_num = 0
    for name in failed_names:
        c = report["checks"][name]
        if name == "mypy":
            for issue in c.get("issues", [])[:20]:
                item_num += 1
                lines.append(
                    f"{item_num}. `{issue['file']}:{issue['line']}` (mypy) — {issue['msg']}"
                )
                files_touched.add(issue["file"])
        elif name == "ruff_lint":
            for issue in c.get("issues", [])[:20]:
                item_num += 1
                lines.append(
                    f"{item_num}. `{issue['file']}:{issue['line']}` (ruff {issue['code']}) — {issue['msg']}"
                )
                files_touched.add(issue["file"])
        elif name == "pytest":
            for fail in c.get("failures", [])[:20]:
                item_num += 1
                lines.append(f"{item_num}. `{fail['nodeid']}` (pytest) — {fail['msg']}")
        elif name == "ruff_format":
            item_num += 1
            tail = (c.get("stdout", "") or c.get("stderr", "")).strip().splitlines()[-5:]
            lines.append(f"{item_num}. ruff format would reformat — tail: `{' / '.join(tail)}`")
        else:
            item_num += 1
            tail = (c.get("stdout", "") or c.get("stderr", "")).strip().splitlines()[-5:]
            lines.append(f"{item_num}. {name} failed — tail: `{' / '.join(tail)}`")

    lines.append("")
    lines.append("## Suggested scope")
    if files_touched:
        lines.append("Touch only these files (and their direct tests):")
        for f in sorted(files_touched):
            lines.append(f"- `{f}`")
    else:
        lines.append(
            "No specific files identified. Inspect the report at `.build/verify_report.json`."
        )
    lines.append("")
    lines.append("Make the smallest fix that turns `make verify` green. Do not add features.")
    lines.append(
        f"If this is attempt {MAX_ATTEMPTS} and still failing, stop and report to the human."
    )
    return "\n".join(lines) + "\n"


def crash_brief(reason: str) -> str:
    return (
        f"# Repair brief — {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
        f"Attempt {attempts_so_far() + 1} of {MAX_ATTEMPTS}.\n\n"
        "## Verify script crashed\n"
        f"```\n{reason}\n```\n\n"
        "Inspect `.build/verify_report.json` if present, otherwise run "
        "`uv run python scripts/verify.py` interactively and read the traceback.\n"
    )


def main() -> int:
    BUILD_DIR.mkdir(exist_ok=True)
    if not REPORT_PATH.exists():
        BRIEF_PATH.write_text(
            crash_brief("No verify_report.json present. Did verify.py run at all?")
        )
        print(f"wrote {BRIEF_PATH.relative_to(REPO_ROOT)} (no report found)")
        return 0
    try:
        report = json.loads(REPORT_PATH.read_text())
    except json.JSONDecodeError as exc:
        BRIEF_PATH.write_text(crash_brief(f"verify_report.json malformed: {exc}"))
        print(f"wrote {BRIEF_PATH.relative_to(REPO_ROOT)} (malformed report)")
        return 0

    if report.get("overall") == "pass":
        # No brief needed; clean up any stale one
        if BRIEF_PATH.exists():
            BRIEF_PATH.unlink()
        print("verify passed; no brief written")
        return 0

    BRIEF_PATH.write_text(render_brief(report))
    print(f"wrote {BRIEF_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
