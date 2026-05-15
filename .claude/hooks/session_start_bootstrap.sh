#!/usr/bin/env bash
# SessionStart hook — surface plan state and bootstrap hints.
#
# Read-only: parses markdown via scripts/status.py. Safe before `uv sync`
# because status.py imports only stdlib.
set -u

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

if ! command -v uv >/dev/null 2>&1; then
    cat <<'EOF'
{"systemMessage": "uv not installed. Run `bash scripts/bootstrap.sh` to set up the environment."}
EOF
    exit 0
fi

# status.py is stdlib-only and won't fail if deps aren't installed
SHORT=$(python3 scripts/status.py --short 2>/dev/null || true)
if [ -n "$SHORT" ]; then
    printf '{"systemMessage": "Plan state: %s. Read CLAUDE.md for the build loop. Use /status, /build, /repair."}\n' "$SHORT"
fi

exit 0
