#!/usr/bin/env bash
set -u

cd "${CODEX_PROJECT_DIR:-$(pwd)}" || exit 0

if python3 scripts/toolset_review.py >/dev/null 2>&1; then
    if [ -f .build/toolset_review.md ]; then
        printf 'Toolset review updated: .build/toolset_review.md\n'
    fi
fi

exit 0

