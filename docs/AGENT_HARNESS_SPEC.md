# Agent Harness Spec

This document specifies the repo-local agent harness for Deep-Sound. It is adjacent to the product spec in [docs/SPEC.md](docs/SPEC.md), not a replacement for it.

## Purpose

The harness exists to keep AI implementation work aligned with:

- the product contract in [docs/SPEC.md](docs/SPEC.md),
- the frontend-neutral agent contract in [docs/build/AGENT_CONTRACT.md](docs/build/AGENT_CONTRACT.md),
- the phase ceiling in [docs/build/PHASES.md](docs/build/PHASES.md),
- the file backlog in [docs/build/FILE_PLAN.md](docs/build/FILE_PLAN.md),
- the verification and repair flow in `scripts/`.

The harness is a dual-surface design:

- `.claude/` remains the existing Claude Code surface.
- `.codex/` is the Codex-native mirror surface added for this repo.
- `docs/` and `scripts/` are the shared source of truth both surfaces must follow.

## Authoritative Inputs

All agents and hooks must treat these files as the highest-priority repo-local inputs:

1. [docs/SPEC.md](docs/SPEC.md)
2. [AGENTS.md](AGENTS.md)
3. [docs/build/AGENT_CONTRACT.md](docs/build/AGENT_CONTRACT.md)
4. [docs/build/PHASES.md](docs/build/PHASES.md)
5. [docs/build/FILE_PLAN.md](docs/build/FILE_PLAN.md)
6. [docs/build/DECISIONS.md](docs/build/DECISIONS.md)
7. [docs/build/BUILD_LOG.md](docs/build/BUILD_LOG.md)

Supporting summaries in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATA_MODEL.md](docs/DATA_MODEL.md), and [docs/PIPELINE.md](docs/PIPELINE.md) are authoritative only insofar as they stay consistent with `docs/SPEC.md`.

## Shared Behavioral Contract

Every agent surface must obey the same operational rules:

- Read current build state before acting.
- Repair takes priority when `.build/repair_brief.md` exists.
- Do not edit `docs/build/FILE_PLAN.md` directly; use `scripts/update_plan.py`.
- Do not implement past `ACTIVE_PHASE`.
- Do not bypass `make verify`.
- Treat confidence-carrying outputs as probabilistic, never definitive.
- Respect service boundaries in spec section 10.2.
- Never modify original imported audio.

## Priority Override Rule

The standard picker rule is still the default. A harness-first pass may temporarily override it only when all of the following are true:

1. The work is repo-control-plane work, not product feature work.
2. The change improves agent safety, spec adherence, auditability, or repairability.
3. The override is recorded in [docs/build/DECISIONS.md](docs/build/DECISIONS.md) and [docs/build/BUILD_LOG.md](docs/build/BUILD_LOG.md).
4. The override does not silently relax product-spec constraints.

When the control-plane pass is complete, agents return to normal FILE_PLAN-driven execution.

## Codex Surface

The Codex harness lives under `.codex/` and contains:

- `README.md`: entrypoint and workflow.
- `CODEX_AGENT_MAP.md`: role selection and delegation rules.
- `agents/`: bounded subagent role prompts.
- `skills/`: short, trigger-oriented skills.
- `hooks/`: repo-local shell hooks that surface state and run suggest-only review tasks.

The `.codex/` surface reuses the existing backend scripts in `scripts/`. It must not fork them into a second implementation unless a later decision explicitly approves that split.

## Self-Review Suggestion Flow

Self-review is suggest-only. It must not auto-edit the harness.

The current mechanism is:

1. Run `python3 scripts/toolset_review.py`.
2. Optionally run `python3 scripts/repo_dive.py --strict` first when history-backed evidence is useful.
3. The script inspects repo state, verify output, repair attempts, repo-dive output when present, and harness coverage.
4. It writes:
   - `.build/toolset_review.json`
   - `.build/toolset_review.md`
5. Hooks may surface those artifacts, but must not apply their recommendations automatically.

Recommendation classes:

- missing skill
- missing hook
- missing review role
- repeated repair pattern
- verification blind spot
- doc drift
- history-backed detector watch

Every recommendation should include evidence, a concrete proposed addition, and a safety level.

## Hook Contract

Repo-local hooks are shell scripts under `.claude/hooks/` and `.codex/hooks/`.

Hook rules:

- Hooks may read repo state and write `.build/` artifacts.
- Hooks must degrade safely when `uv` or dependencies are unavailable.
- Hooks must not mutate tracked source files.
- Hooks must emit concise operator-facing guidance.

Current Codex hook intent:

- `session_start_status.sh`: run `scripts/session_start.py` and surface repair state.
- `stop_self_review.sh`: run the suggest-only toolset review and surface any recommendations.

## History Dive Contract

`scripts/repo_dive.py` is a read-only audit command for git/build/test history. It writes `.build/repo_dive_report.json` and `.build/repo_dive_report.md`, degrades cleanly with `--no-git`, and fails `--strict` only for high-severity current detector failures.

The durable curated summary is [docs/build/REPO_DIVE.md](docs/build/REPO_DIVE.md). Generated `.build/` reports are evidence, not tracked source-of-truth docs.

Repo-dive detectors are registry-based. New checks should be added as detectors instead of one-off report branches.

## Subagent Policy

Subagents are allowed and encouraged when their scope is bounded.

Rules:

- Use read-only exploration roles for repo audit, MIR review, and verification interpretation.
- Use `history-auditor` and `dependency-gate-auditor` as read-only roles when history or optional-gate evidence matters.
- Use coding roles only with explicit file ownership and no overlap.
- Prefer subagents for sidecar work, not for the immediate blocking task.
- Every delegated coding task must return changed files and validation results.

## Validation Surface

Harness changes are considered healthy when:

- `python3 scripts/status.py` still reports build state correctly.
- `python3 scripts/toolset_review.py` succeeds and emits structured artifacts.
- `python3 scripts/verify.py` still produces the expected report contract when dependencies are available.
- `.claude/` and `.codex/` both point back to the same authoritative docs and scripts.
