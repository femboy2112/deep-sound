---
description: Pick the next TODO from FILE_PLAN and implement it.
allowed-tools: Read, Bash, Edit, Write, Glob, Grep, Task
---

Execute the **Build loop** documented in `CLAUDE.md`. Concretely:

1. If `.build/repair_brief.md` exists, run `/repair` instead and stop.
2. Run `uv run python scripts/status.py` to identify the next TODO row.
3. Read the matching row from `docs/build/FILE_PLAN.md` (the script tells you the id).
4. Mark it IN_PROGRESS: `uv run python scripts/update_plan.py --id <id> --status IN_PROGRESS --last-attempt now`.
5. Extract the relevant spec sections referenced in `spec_refs` from `docs/SPEC.md` (do **not** load the full spec).
6. Read each `depends_on` file so the build-engineer has its context.
7. Dispatch the `build-engineer` subagent via the Task tool with:
   - The row (id, path, summary, verify command).
   - The extracted spec sections (verbatim quotes).
   - The contents of dependency files.
8. After the subagent returns, run `uv run python scripts/verify.py`.
   - PASS → mark DONE: `uv run python scripts/update_plan.py --id <id> --status DONE`. Append a `docs/build/BUILD_LOG.md` entry. Commit with `feat(<area>): <summary>` and trailer `Plan-Id: <id>`.
   - FAIL → leave IN_PROGRESS. The Stop hook will produce a repair brief.
9. Report the outcome to the user in one line.

Never edit `docs/build/FILE_PLAN.md` directly. Settings deny it.
