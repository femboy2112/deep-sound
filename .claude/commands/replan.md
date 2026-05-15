---
description: Re-derive FILE_PLAN rows from spec drift or new requirements.
allowed-tools: Read, Bash, Task, Edit
argument-hint: [scope-hint, e.g. "Phase 1 storage" or "all"]
---

Dispatch the `planner` subagent via the Task tool to propose FILE_PLAN updates given the current spec and the argument hint `$ARGUMENTS`.

The planner must:

1. Read `docs/SPEC.md`, `docs/build/PHASES.md`, and the current `docs/build/FILE_PLAN.md`.
2. Identify rows that are missing, redundant, or mis-scoped relative to the spec section it covers.
3. Propose adds/removes/edits as a unified diff or as a list of `scripts/update_plan.py` invocations.
4. **Not** execute changes — return the proposal for human review.

After the planner returns, surface the proposal to the user and ask whether to apply it. Only apply with explicit confirmation, then commit:

```
docs(plan): replan $ARGUMENTS

Plan-Id: replan
```
