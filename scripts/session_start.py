"""Print a compact repo startup summary for human or agent operators."""

from __future__ import annotations

import shutil

import status as build_status


def main() -> int:
    if shutil.which("uv") is None:
        print(
            "uv not installed. Run `bash scripts/bootstrap.sh` if you need dependency-backed commands."
        )

    print("Shared contract: docs/build/AGENT_CONTRACT.md")
    if build_status.BRIEF_PATH.exists():
        print("Repair brief present: address it before new work.")

    return build_status.main()


if __name__ == "__main__":
    raise SystemExit(main())
