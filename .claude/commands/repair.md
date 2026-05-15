---
description: Fix the last verify failure using .build/repair_brief.md.
allowed-tools: Read, Bash, Edit, Task
---

Execute the **Repair loop** from `CLAUDE.md`:

1. Read `.build/repair_brief.md`. If missing, tell the user and stop.
2. Read `.build/verify_report.json` for full detail.
3. Read `.build/repair_attempts.txt` (default 0 if missing). If the value is `>= 3`, **refuse**: print the brief and stop. Do not retry.
4. Otherwise increment the counter:
   ```bash
   mkdir -p .build
   n=$(cat .build/repair_attempts.txt 2>/dev/null || echo 0)
   echo $((n+1)) > .build/repair_attempts.txt
   ```
5. Dispatch the `repair-engineer` subagent via the Task tool, passing the brief contents and the failing items. Constrain it to the files listed in the brief's "Suggested scope" section. No new features.
6. After the subagent returns, run `uv run python scripts/verify.py`.
   - PASS → `rm .build/repair_brief.md && echo 0 > .build/repair_attempts.txt`. Tell the user "repair green". The user (or `/continue`) resumes building.
   - FAIL → the Stop hook will re-write the brief next turn. Loop back to step 3.

If the brief reports that verify itself crashed, fix the verify pipeline (e.g. missing import in `scripts/verify.py` or broken `pyproject.toml`) before anything else.
