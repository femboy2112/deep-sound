---
description: Print FILE_PLAN summary, active phase, repair-brief presence.
allowed-tools: Bash, Read
---

Run `uv run python scripts/status.py` (or `python3 scripts/status.py` if uv is unavailable) and print the output verbatim.

If the output indicates a repair brief is present, remind the user that `/repair` must run before more building.

If `ACTIVE_PHASE` looks exhausted (no eligible TODO), suggest `/phase <n+1>` to promote — but do not switch the phase automatically.
