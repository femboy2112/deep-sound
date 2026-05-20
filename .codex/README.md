# Deep-Sound Codex Surface

This directory is the Codex-native mirror of the existing `.claude/` control plane. It does not replace the shared repo rules in [AGENTS.md](../AGENTS.md) or the product contract in [docs/SPEC.md](../docs/SPEC.md).

## Read Order

1. [../AGENTS.md](../AGENTS.md)
2. [../docs/SPEC.md](../docs/SPEC.md)
3. [../docs/build/AGENT_CONTRACT.md](../docs/build/AGENT_CONTRACT.md)
4. [../docs/build/PHASES.md](../docs/build/PHASES.md)
5. [../docs/build/FILE_PLAN.md](../docs/build/FILE_PLAN.md)
6. [../docs/AGENT_HARNESS_SPEC.md](../docs/AGENT_HARNESS_SPEC.md)
7. [CODEX_AGENT_MAP.md](CODEX_AGENT_MAP.md)

## What Lives Here

- `agents/`: bounded subagent roles for planning, building, verifying, repair, MIR review, and harness review.
- `skills/`: short trigger-oriented skills for domain rules and repo-control-plane work.
- `hooks/`: repo-local helper hooks that surface status and run suggest-only harness review.

## Shared Backend

This surface reuses the existing scripts:

- `python3 scripts/status.py`
- `python3 scripts/session_start.py`
- `python3 scripts/verify.py`
- `python3 scripts/repair.py`
- `python3 scripts/update_plan.py`
- `python3 scripts/toolset_review.py`

Do not fork those scripts into `.codex/scripts/` unless a later decision explicitly approves that split.

## Operating Rules

- Repair first if `.build/repair_brief.md` exists.
- Follow the phase ceiling.
- Use `scripts/update_plan.py` for `FILE_PLAN.md` mutations.
- Keep new work within the requested scope.
- Treat labels and analysis outputs as probabilistic.
- Keep self-review suggest-only.
