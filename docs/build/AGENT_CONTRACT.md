# Agent Contract

This is the frontend-neutral build contract for Deep-Sound. Both `.claude/` and `.codex/` are wrappers over this contract.

## Read order

1. `docs/SPEC.md`
2. `AGENTS.md`
3. `docs/build/PHASES.md`
4. `docs/build/FILE_PLAN.md`
5. `docs/build/DECISIONS.md`
6. `docs/build/BUILD_LOG.md`

## Session start

Use `python3 scripts/session_start.py` for a compact startup summary.

It must:

- work before dependency sync,
- report current phase,
- report the next eligible TODO,
- report repair-brief presence,
- point the operator back to this contract.

## Core loop

1. Read state.
2. Repair first if `.build/repair_brief.md` exists.
3. Otherwise use the normal picker:
   - lowest `id`
   - `status == TODO`
   - all `depends_on` rows are `DONE`
   - `phase <= ACTIVE_PHASE`
4. Implement within scope.
5. Run verify.
6. Record outcome in build docs.

## Hard rules

- Do not edit `docs/build/FILE_PLAN.md` directly.
- Do not implement past `ACTIVE_PHASE`.
- Do not skip verify.
- Do not present inferred labels as definite.
- Do not bypass service boundaries.
- Do not modify imported audio.

## Priority override

A repo-control-plane pass may override the normal picker only when the override is documented in `DECISIONS.md` and `BUILD_LOG.md`, and only when it improves harness safety or spec adherence.

