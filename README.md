# deep-sound

A source-aware music similarity desktop application. Analyzes recorded music, decomposes it into musically meaningful source-level representations (drums, bass, harmonic sources, etc.), and searches a local library for songs, sections, or sources similar along selected dimensions (rhythm, chord progression, timbre, bassline, production).

See [`docs/SPEC.md`](docs/SPEC.md) for the full product spec.

Repo-control-plane docs live in:

- [`docs/AGENT_HARNESS_SPEC.md`](docs/AGENT_HARNESS_SPEC.md)
- [`docs/REPO_AUDIT.md`](docs/REPO_AUDIT.md)
- [`docs/build/AGENT_CONTRACT.md`](docs/build/AGENT_CONTRACT.md)

## Status

This repository is in **Phase 10 optional real-source smoke**. Phase 9 completed the interactive desktop beta hardening seam; Phase 10 keeps the default fake-provider `source_aware` path while adding explicit `source_aware_real` routing for local Demucs smoke tests.

## Quickstart

```bash
# One-time setup
bash scripts/bootstrap.sh        # installs uv if missing, runs uv sync --extra dev

# Try the CLI/service beta path
uv run deep-sound analyze-library --library-db /tmp/deep-sound.sqlite --import-path path/to/audio --profile searchable
uv run deep-sound index-library --library-db /tmp/deep-sound.sqlite --profile searchable

# Optional real-source smoke when Demucs is installed intentionally
uv run deep-sound analyze-library --library-db /tmp/deep-sound-real.sqlite --import-path path/to/audio --profile source_aware_real

# Run quality gates
make verify                       # ruff + mypy + pytest

# See what's done and what's next
make status
```

## How the build loop works

This repo is designed so an AI agent (Claude Code or Codex) can iteratively build the application using simple slash commands:

| Command | What it does |
|---|---|
| `/build` (or `continue`) | Picks the next TODO from [`docs/build/FILE_PLAN.md`](docs/build/FILE_PLAN.md), implements it, verifies, commits |
| `/repair` | Fixes the last verification failure using `.build/repair_brief.md` |
| `/verify` | Runs ruff + mypy + pytest |
| `/status` | Prints plan summary, active phase, repair-brief presence |
| `/phase <n>` | Promotes the active build phase; see [`docs/build/PHASES.md`](docs/build/PHASES.md) |
| `/replan` | Re-derives FILE_PLAN rows from spec updates |

For Claude Code, see [`CLAUDE.md`](CLAUDE.md). For Codex, see [`AGENTS.md`](AGENTS.md).

The repo now also carries a Codex-native mirror surface in [`.codex/`](.codex/) that reuses the same `docs/build/*` and `scripts/*` backend as `.claude/`.

## Self-repair

A Claude Code `Stop` hook runs `scripts/verify.py` whenever the agent stops. On failure, `scripts/repair.py` writes `.build/repair_brief.md` with `file:line` context. The agent is prompted to invoke `/repair` next, which dispatches a focused fix. A counter caps the loop at 3 attempts.

## Layout

```
docs/                    Spec, distilled architecture/data-model/pipeline docs, build/
docs/build/              FILE_PLAN.md (living backlog) · PHASES.md · BUILD_LOG.md · DECISIONS.md
src/deep_sound/          App code: domain/, services/, infra/, cli.py
tests/                   pytest tests
scripts/                 verify.py, repair.py, status.py, update_plan.py, bootstrap.sh
.claude/                 Claude Code orchestration: commands/, agents/, skills/, hooks/, settings.json
.codex/                  Codex orchestration: agents/, skills/, hooks/, and entry docs
```

## License

MIT — see [LICENSE](LICENSE).
