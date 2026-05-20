"""Print a compact operator summary of the shared Deep-Sound build contract."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "docs" / "build" / "AGENT_CONTRACT.md"


def main() -> int:
    print(CONTRACT_PATH.read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
