"""Pretty-print FILE_PLAN summary, active phase, and repair-brief presence.

Read-only. Safe to run before `uv sync` because it only parses markdown.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASES_PATH = REPO_ROOT / "docs" / "build" / "PHASES.md"
PLAN_PATH = REPO_ROOT / "docs" / "build" / "FILE_PLAN.md"
BRIEF_PATH = REPO_ROOT / ".build" / "repair_brief.md"

ACTIVE_PHASE_RE = re.compile(r"^\*\*ACTIVE_PHASE:\*\*\s*(\d+)\s*$", re.MULTILINE)


def read_active_phase() -> int | None:
    if not PHASES_PATH.exists():
        return None
    m = ACTIVE_PHASE_RE.search(PHASES_PATH.read_text())
    return int(m.group(1)) if m else None


def parse_plan_rows() -> list[dict[str, str]]:
    if not PLAN_PATH.exists():
        return []
    rows: list[dict[str, str]] = []
    in_table = False
    headers: list[str] = []
    for line in PLAN_PATH.read_text().splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not headers:
                # First | line is the header
                headers = cells
                continue
            if all(set(c) <= set("-: ") for c in cells):
                # Separator row
                in_table = True
                continue
            if in_table and len(cells) == len(headers):
                rows.append(dict(zip(headers, cells, strict=True)))
        else:
            if in_table:
                # Blank or non-table line ends the table
                in_table = False
                headers = []
    return rows


def deps_done(row: dict[str, str], done_ids: set[str]) -> bool:
    raw = row.get("depends_on", "").strip()
    if not raw or raw == "-":
        return True
    return all(dep.strip() in done_ids for dep in raw.split(","))


def pick_next(rows: list[dict[str, str]], active_phase: int) -> dict[str, str] | None:
    done = {r["id"] for r in rows if r.get("status") == "DONE"}
    todos = [
        r
        for r in rows
        if r.get("status") == "TODO"
        and int(r.get("phase", "99")) <= active_phase
        and deps_done(r, done)
    ]
    return min(todos, key=lambda r: r["id"]) if todos else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short", action="store_true", help="One-line summary only")
    args = parser.parse_args()

    active = read_active_phase()
    rows = parse_plan_rows()
    counts = Counter(r.get("status", "?") for r in rows)
    nxt = pick_next(rows, active) if active is not None else None
    brief = BRIEF_PATH.exists()

    if args.short:
        next_id = nxt["id"] if nxt else "none"
        print(
            f"phase={active} todo={counts.get('TODO', 0)} done={counts.get('DONE', 0)} "
            f"in_progress={counts.get('IN_PROGRESS', 0)} next={next_id} repair_brief={'yes' if brief else 'no'}"
        )
        return 0

    print(f"ACTIVE_PHASE: {active}")
    print(f"FILE_PLAN ({PLAN_PATH.relative_to(REPO_ROOT)}):")
    for status in ["TODO", "IN_PROGRESS", "DONE", "BLOCKED", "FAILED"]:
        if counts.get(status, 0):
            print(f"  {status:12s} {counts[status]}")
    if nxt:
        print(f"\nNext TODO: {nxt['id']}  {nxt['path']}")
        print(f"  summary: {nxt['summary']}")
        print(f"  spec:    {nxt['spec_refs']}")
        print(f"  verify:  {nxt['verify']}")
    else:
        print("\nNext TODO: none (phase exhausted or blocked)")
    print(f"\nRepair brief present: {'YES — run /repair' if brief else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
