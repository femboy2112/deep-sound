# AGENTS.md — Deep-Sound (for Codex and compatible agents)

A Python 3.11 desktop app for source-aware music similarity. Full spec: `docs/SPEC.md`.

## Project layout

- `src/deep_sound/` — application code: `domain/`, `services/`, `infra/`, `cli.py`.
- `tests/` — pytest suite.
- `scripts/` — `verify.py`, `repair.py`, `status.py`, `update_plan.py`, `bootstrap.sh`.
- `docs/build/` — living plan: `FILE_PLAN.md`, `PHASES.md`, `BUILD_LOG.md`, `DECISIONS.md`.
- `docs/AGENT_HARNESS_SPEC.md` — shared control-plane contract for `.claude/` and `.codex/`.
- `docs/REPO_AUDIT.md` — repo-wide audit of product and harness surfaces.
- `.claude/` — Claude Code orchestration; safe to ignore if running Codex.
- `.codex/` — Codex orchestration: agents, skills, hooks, and repo-local role maps.

## Build commands

| Command | Purpose |
|---|---|
| `make bootstrap` | Install `uv` if missing, run `uv sync --extra dev`. |
| `make verify` | Run ruff + mypy + pytest. Writes `.build/verify_report.json`. |
| `make repair` | Print `.build/repair_brief.md` if a failure is pending. |
| `make status` | Print FILE_PLAN summary and active phase. |
| `make phase` | Print the current `ACTIVE_PHASE`. |

## The loop

1. **Read state** — `docs/build/PHASES.md` (find `**ACTIVE_PHASE:** N`), then `make status`.
2. **Repair first** — if `.build/repair_brief.md` exists, fix what it lists before new work.
3. **Pick next TODO** — from `docs/build/FILE_PLAN.md`, lowest `id` whose `status=TODO`, all `depends_on` are `DONE`, and `phase <= ACTIVE_PHASE`.
4. **Implement** — write/edit the file at `path`. Consult the `spec_refs` columns and read the relevant spec sections.
5. **Verify** — run `make verify`.
6. **Mark and log** — `python scripts/update_plan.py --id <id> --status DONE` and append a `BUILD_LOG.md` entry.
7. **Commit** — Conventional Commits, include `Plan-Id: <id>` trailer.

## Style

- `ruff format` then `ruff check` (config in `ruff.toml`).
- `mypy --strict` on `src/deep_sound`.
- `pytest` for tests.
- Type hints on every public function.

## Domain rules from the spec

- **§3.3 / §23 — Confidence policy.** Every inferred label, source, chord, or event carries a `confidence: float` in `[0, 1]`. Never present a label as definite.
- **§10.2 — Service boundaries.** Library, Analysis, Source, Feature, Similarity, Explanation services have public surfaces; cross-service calls go through them.
- **§17 — Storage policy.** Original audio files MUST NOT be modified. Analysis copies and stems live under `app_data/` (gitignored). Every artifact records algorithm name, version, parameters hash, model version.
- **§19 — Phasing.** Phases progress through the active plan in `docs/build/PHASES.md`. Don't build beyond `ACTIVE_PHASE`.
- **Harness rule.** Repo-control-plane work may temporarily override the normal picker only when documented in `docs/AGENT_HARNESS_SPEC.md`, `docs/build/DECISIONS.md`, and `docs/build/BUILD_LOG.md`.

## Don't

- Don't hand-edit `docs/build/FILE_PLAN.md` — use `scripts/update_plan.py`.
- Don't skip `make verify`. If the gate is wrong, fix the gate properly, don't bypass it.
- Don't add features outside the current FILE_PLAN row's scope.
- Don't commit with `--no-verify`.
- Don't install heavy extras (`demucs`, `ui`, `index`) unless the current row requires them.

## Self-repair

When you finish a session and `make verify` fails, `scripts/repair.py` produces `.build/repair_brief.md`. Open it next session and fix only what it lists. Cap: 3 attempts (tracked in `.build/repair_attempts.txt`). If you hit the cap, stop and report to the human.

## Codex harness

If you are running Codex, also read:

- `.codex/README.md`
- `.codex/CODEX_AGENT_MAP.md`

Use `make toolset-review` or `python3 scripts/toolset_review.py` when you need a suggest-only review of missing skills, hooks, or other harness additions.
