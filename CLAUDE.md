# Deep-Sound — Build Orchestration (Claude Code)

You are an AI coding agent iteratively building a source-aware music similarity desktop application. The full product spec is in [`docs/SPEC.md`](docs/SPEC.md). The phased build plan is in [`docs/build/PHASES.md`](docs/build/PHASES.md). The per-file backlog is [`docs/build/FILE_PLAN.md`](docs/build/FILE_PLAN.md).

## First, read the state

Every session, before doing anything else:

1. Read [`docs/build/PHASES.md`](docs/build/PHASES.md) and find the line starting with `**ACTIVE_PHASE:** N`. That is the build ceiling.
2. Run `python scripts/status.py` for a one-screen summary (counts, next TODO id, repair-brief presence).
3. Read the tail of [`docs/build/BUILD_LOG.md`](docs/build/BUILD_LOG.md) for recent decisions.
4. If `.build/repair_brief.md` exists, **repair takes priority over new work** — run `/repair`.

## Picker rule (which file to build next)

From `FILE_PLAN.md`, pick the lowest `id` row where:

- `status == TODO`
- every id in `depends_on` has `status == DONE`
- `phase <= ACTIVE_PHASE`

If no such row exists, the phase is complete. Report this to the user; do not advance phase without explicit instruction.

## Build loop (`/build` or `/continue`)

1. If `.build/repair_brief.md` exists → invoke `/repair` instead. Stop.
2. Pick the next TODO via the picker rule.
3. Mark IN_PROGRESS: `python scripts/update_plan.py --id <id> --status IN_PROGRESS`.
4. Dispatch the `build-engineer` subagent (via Task tool) with:
   - the FILE_PLAN row (id, path, summary, verify command),
   - the relevant `spec_refs` sections (extract from `docs/SPEC.md` — do NOT paste the whole spec),
   - file contents of each `depends_on` path.
5. After it returns, run `python scripts/verify.py`.
   - PASS → mark DONE: `python scripts/update_plan.py --id <id> --status DONE`. Append a BUILD_LOG entry. Commit (see below).
   - FAIL → leave IN_PROGRESS. The Stop hook will write a repair brief.
6. Loop until the active phase is exhausted or the user stops you.

## Repair loop (`/repair`)

1. Read `.build/repair_brief.md` and `.build/verify_report.json`.
2. Read `.build/repair_attempts.txt`. If its value is `>= 3`, **refuse**: print the brief to the user and stop. Do not retry.
3. Otherwise increment the counter (`echo $((n+1)) > .build/repair_attempts.txt`) and dispatch `repair-engineer` with the brief.
4. Re-run `python scripts/verify.py`.
   - PASS → `rm .build/repair_brief.md && echo 0 > .build/repair_attempts.txt`. Resume the build loop.
   - FAIL → loop back to step 2.

## Commit conventions

- Conventional commits: `feat(<area>): <summary>`, `fix`, `chore`, `docs`, `test`, `refactor`.
- Include the FILE_PLAN id in the trailer: `Plan-Id: P0-007`.
- One commit per FILE_PLAN row when possible.
- Never amend prior commits during a build cycle.
- Never use `--no-verify`.

## Hard rules

- **Never edit `docs/build/FILE_PLAN.md` directly.** Settings explicitly deny that path. Use `scripts/update_plan.py`.
- **Never skip the gates.** If ruff/mypy/pytest disagree with you, fix the code, not the gate.
- **Confidence policy (spec §3.3, §23).** Every inferred label or event MUST carry a `confidence` float in `[0, 1]`. No exceptions, even for stubs.
- **Service boundaries (spec §10.2) are non-negotiable.** Route cross-service calls through public interfaces.
- **Phase gating.** Do not implement files whose `phase > ACTIVE_PHASE`. If you believe a row should move phases, propose it via `/replan` rather than acting unilaterally.
- **Original audio is untouchable** (spec §17). Never modify imported audio files. Analysis copies live under `app_data/` (gitignored).

## Where to find what

| Need | File |
|---|---|
| Full product spec | `docs/SPEC.md` |
| Architecture summary | `docs/ARCHITECTURE.md` |
| Data model summary | `docs/DATA_MODEL.md` |
| Pipeline summary | `docs/PIPELINE.md` |
| Phase definitions | `docs/build/PHASES.md` |
| File backlog | `docs/build/FILE_PLAN.md` |
| Build journal | `docs/build/BUILD_LOG.md` |
| Past decisions | `docs/build/DECISIONS.md` |
| Domain skills | `.claude/skills/*` (auto-invoked by keywords) |
| Subagents | `.claude/agents/*` |

## Subagent dispatch quick reference

| Task | Agent |
|---|---|
| Implement one FILE_PLAN row | `build-engineer` |
| Run the gates and interpret results | `verifier` |
| Fix a failed verify | `repair-engineer` |
| Update FILE_PLAN / PHASES | `planner` |
| Review audio/MIR code against spec | `mir-domain-expert` |
