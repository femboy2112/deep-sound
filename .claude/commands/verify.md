---
description: Run ruff + mypy + pytest, summarize result.
allowed-tools: Bash, Read
---

Run `uv run python scripts/verify.py` and summarize the outcome:

- Print the overall pass/fail and per-check status.
- If any check failed, list the first 5 issues from `.build/verify_report.json` with file:line context.
- Mention whether `.build/repair_brief.md` was produced (the Stop hook writes it; this command does not).

Do not implement fixes here — that is the job of `/repair`.
