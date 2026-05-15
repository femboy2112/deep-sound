#!/usr/bin/env bash
# Stop hook — self-repair trigger.
#
# Runs scripts/verify.py whenever the agent stops. On failure, writes
# .build/repair_brief.md and prints a systemMessage telling the next turn
# to invoke /repair. Guards against overwriting an unresolved brief.
set -u

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# Guard: don't trample an already-pending brief
if [ -f .build/repair_brief.md ]; then
    cat <<'EOF'
{"systemMessage": "A repair brief is already pending at .build/repair_brief.md. Run /repair to address it before continuing."}
EOF
    exit 0
fi

# Only fire if uv is available — pre-bootstrap sessions skip
if ! command -v uv >/dev/null 2>&1; then
    exit 0
fi

# Run verify silently
if uv run python scripts/verify.py >/dev/null 2>&1; then
    # Green — nothing to do
    exit 0
fi

# Red — produce brief
uv run python scripts/repair.py >/dev/null 2>&1 || true

if [ -f .build/repair_brief.md ]; then
    cat <<'EOF'
{"systemMessage": "Verify failed. Repair brief written to .build/repair_brief.md. Run /repair to address it."}
EOF
fi

exit 0
