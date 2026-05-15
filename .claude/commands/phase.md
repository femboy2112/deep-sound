---
description: Print or promote the ACTIVE_PHASE in PHASES.md.
allowed-tools: Read, Bash, Edit
argument-hint: [phase number 0-5, or omit to print]
---

If `$ARGUMENTS` is empty: print the current `ACTIVE_PHASE` via `uv run python scripts/update_plan.py --print-phase`.

If `$ARGUMENTS` is a digit `0`–`5`:

1. Show the current phase first.
2. Confirm with the user that the current phase's exit criteria (in `docs/build/PHASES.md`) are met. List unfinished rows of that phase from FILE_PLAN with `make status`.
3. Only on explicit confirmation, edit the line `**ACTIVE_PHASE:** N` in `docs/build/PHASES.md` to the new value.
4. Commit:
   ```
   chore(phase): promote ACTIVE_PHASE to N

   Plan-Id: phase
   ```

Never silently jump phases.
