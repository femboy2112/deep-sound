#!/usr/bin/env bash
# Install uv if missing, then sync the dev environment.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Installing..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "ERROR: neither curl nor wget available. Install uv manually: https://docs.astral.sh/uv/" >&2
        exit 1
    fi
    # uv installs to ~/.local/bin; make it available for the rest of this script
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Using uv: $(uv --version)"
uv sync --extra dev
echo "Bootstrap complete. Try:  uv run deep-sound --help"
