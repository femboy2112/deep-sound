"""Programmatic mutator for docs/build/FILE_PLAN.md.

Single allowed path for editing the FILE_PLAN table. Uses fcntl.flock to
serialize concurrent sessions. Operations:

  --id <id> --status <state>           Change a row's status
  --id <id> --note "..."               Append to a row's notes
  --id <id> --last-attempt now|ISO     Stamp last_attempt
  --add-row                            Add a new row from full column values
  --print-phase                        Print ACTIVE_PHASE from PHASES.md
  --list                               Pretty-print all rows
  --dry-run                            Show what would change, don't write
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = REPO_ROOT / "docs" / "build" / "FILE_PLAN.md"
PHASES_PATH = REPO_ROOT / "docs" / "build" / "PHASES.md"

VALID_STATUSES = {"TODO", "IN_PROGRESS", "DONE", "BLOCKED", "FAILED"}
ACTIVE_PHASE_RE = re.compile(r"^\*\*ACTIVE_PHASE:\*\*\s*(\d+)\s*$", re.MULTILINE)
ROW_ID_RE = re.compile(r"^P\d+-\d{3}$")
REQUIRED_HEADERS = [
    "id",
    "path",
    "phase",
    "spec_refs",
    "status",
    "depends_on",
    "owner_agent",
    "summary",
    "verify",
    "last_attempt",
    "notes",
]


def find_table_bounds(text: str) -> tuple[int, int, list[str]]:
    """Return (header_line_idx, last_row_idx_exclusive, headers)."""
    lines = text.splitlines()
    header_idx: int | None = None
    sep_idx: int | None = None
    end_idx: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("|") and header_idx is None and "id" in line and "path" in line:
            header_idx = i
        elif header_idx is not None and sep_idx is None and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                sep_idx = i
        elif sep_idx is not None and not line.startswith("|"):
            end_idx = i
            break
    if header_idx is None or sep_idx is None:
        raise RuntimeError("Could not locate FILE_PLAN table.")
    if end_idx is None:
        end_idx = len(lines)
    headers = [c.strip() for c in lines[header_idx].strip().strip("|").split("|")]
    return sep_idx + 1, end_idx, headers


def parse_row(line: str, headers: list[str]) -> dict[str, str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != len(headers):
        raise RuntimeError(f"Row has {len(cells)} cells, expected {len(headers)}: {line!r}")
    return dict(zip(headers, cells, strict=True))


def render_row(row: dict[str, str], headers: list[str]) -> str:
    return "| " + " | ".join(row.get(h, "") for h in headers) + " |"


def validate_headers(headers: list[str]) -> None:
    missing = [header for header in REQUIRED_HEADERS if header not in headers]
    if missing:
        raise SystemExit(f"FILE_PLAN table missing required columns: {', '.join(missing)}")


def validate_row_id(row_id: str) -> None:
    if not ROW_ID_RE.match(row_id):
        raise SystemExit(f"Invalid row id {row_id!r}; expected format like P2-001")


def validate_depends_on(raw: str, existing_ids: set[str], row_id: str) -> None:
    if raw == "-":
        return
    if not raw:
        raise SystemExit("depends_on is required; use '-' for no dependencies")
    deps = [dep.strip() for dep in raw.split(",")]
    if any(not dep for dep in deps):
        raise SystemExit(f"Malformed depends_on value for {row_id}: {raw!r}")
    for dep in deps:
        validate_row_id(dep)
        if dep == row_id:
            raise SystemExit(f"Row {row_id} cannot depend on itself")
        if dep not in existing_ids:
            raise SystemExit(f"Row {row_id} depends on unknown id {dep}")


def validate_new_row(row: dict[str, str], headers: list[str], existing_ids: set[str]) -> None:
    validate_headers(headers)
    for header in REQUIRED_HEADERS:
        if not row.get(header):
            raise SystemExit(f"--{header.replace('_', '-')} is required when using --add-row")
    validate_row_id(row["id"])
    if row["id"] in existing_ids:
        raise SystemExit(f"Row id already exists: {row['id']}")
    try:
        phase = int(row["phase"])
    except ValueError as exc:
        raise SystemExit(f"Invalid phase {row['phase']!r}; expected integer") from exc
    if phase < 0:
        raise SystemExit("phase must be non-negative")
    if row["status"] not in VALID_STATUSES:
        raise SystemExit(f"Invalid status {row['status']!r}. Choose from {sorted(VALID_STATUSES)}")
    validate_depends_on(row["depends_on"], existing_ids, row["id"])


def row_from_args(
    args: argparse.Namespace, headers: list[str], existing_ids: set[str]
) -> dict[str, str]:
    row = {
        "id": args.id or "",
        "path": args.path or "",
        "phase": "" if args.phase is None else str(args.phase),
        "spec_refs": args.spec_refs or "",
        "status": args.status or "",
        "depends_on": args.depends_on or "",
        "owner_agent": args.owner_agent or "",
        "summary": args.summary or "",
        "verify": args.verify or "",
        "last_attempt": args.last_attempt or "-",
        "notes": args.notes or "-",
    }
    validate_new_row(row, headers, existing_ids)
    return row


def sort_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: (int(row.get("phase", "99")), row.get("id", "")))


def mutate(args: argparse.Namespace) -> tuple[str, list[str]]:
    text = PLAN_PATH.read_text()
    start, end, headers = find_table_bounds(text)
    validate_headers(headers)
    lines = text.splitlines()
    rows = [parse_row(lines[i], headers) for i in range(start, end) if lines[i].strip()]

    changes: list[str] = []
    existing_ids = {r["id"] for r in rows}
    if args.add_row:
        row = row_from_args(args, headers, existing_ids)
        rows.append(row)
        rows = sort_rows(rows)
        changes.append(f"{row['id']}: row added")
    else:
        if args.id is None:
            raise SystemExit("--id is required")
        validate_row_id(args.id)
        target = None
        for r in rows:
            if r["id"] == args.id:
                target = r
                break
        if target is None:
            raise SystemExit(f"No row with id={args.id!r}")

        if args.status:
            changes.append(f"{args.id}: status {target['status']} -> {args.status}")
            target["status"] = args.status
        if args.note:
            old = target.get("notes", "")
            new = (old + "; " + args.note).lstrip("; ") if old and old != "-" else args.note
            changes.append(f"{args.id}: notes appended")
            target["notes"] = new
        if args.last_attempt:
            stamp = (
                time.strftime("%Y-%m-%d", time.gmtime())
                if args.last_attempt == "now"
                else args.last_attempt
            )
            changes.append(f"{args.id}: last_attempt -> {stamp}")
            target["last_attempt"] = stamp

    # Re-render the table region
    new_lines = list(lines[:start])
    new_lines.extend(render_row(r, headers) for r in rows)
    new_lines.extend(lines[end:])
    new_text = "\n".join(new_lines)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, changes


def cmd_print_phase() -> int:
    if not PHASES_PATH.exists():
        print("PHASES.md missing", file=sys.stderr)
        return 1
    m = ACTIVE_PHASE_RE.search(PHASES_PATH.read_text())
    if not m:
        print("ACTIVE_PHASE not found in PHASES.md", file=sys.stderr)
        return 1
    print(m.group(1))
    return 0


def cmd_list() -> int:
    text = PLAN_PATH.read_text()
    start, end, headers = find_table_bounds(text)
    lines = text.splitlines()
    for i in range(start, end):
        if lines[i].strip():
            r = parse_row(lines[i], headers)
            print(f"{r['id']:8s} {r['status']:12s} {r['path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--add-row", action="store_true")
    p.add_argument("--id", help="Row id, e.g. P0-007")
    p.add_argument("--status", choices=sorted(VALID_STATUSES))
    p.add_argument("--path", help="Path for --add-row")
    p.add_argument("--phase", type=int, help="Phase for --add-row")
    p.add_argument("--spec-refs", help="Spec references for --add-row")
    p.add_argument("--depends-on", help="Comma-separated dependencies for --add-row, or '-'")
    p.add_argument("--owner-agent", help="Owner agent for --add-row")
    p.add_argument("--summary", help="Summary for --add-row")
    p.add_argument("--verify", help="Verification command for --add-row")
    p.add_argument("--notes", help="Notes value for --add-row")
    p.add_argument("--note", help="Append to notes")
    p.add_argument("--last-attempt", help="ISO date or 'now'")
    p.add_argument("--print-phase", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p


def main_from_args(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.print_phase:
        return cmd_print_phase()
    if args.list:
        return cmd_list()
    if not args.id:
        p.error("--id is required (or use --print-phase / --list)")
    if args.add_row and args.note:
        p.error("--note appends to existing rows; use --notes with --add-row")

    with PLAN_PATH.open("r+") as f:
        with contextlib.suppress(OSError):
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # best-effort lock
        new_text, changes = mutate(args)
        if not changes:
            print("no changes requested")
            return 0
        for c in changes:
            print(c)
        if args.dry_run:
            print("(dry-run: no write)")
            return 0
        f.seek(0)
        f.write(new_text)
        f.truncate()
    return 0


def main() -> int:
    return main_from_args()


if __name__ == "__main__":
    sys.exit(main())
