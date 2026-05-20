#!/usr/bin/env bash
set -u

cd "${CODEX_PROJECT_DIR:-$(pwd)}" || exit 0

python3 scripts/session_start.py 2>/dev/null || true

exit 0
