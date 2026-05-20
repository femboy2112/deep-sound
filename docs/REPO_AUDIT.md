# Repo Audit

This audit inventories the current Deep-Sound repository as of the Codex harness pass on 2026-05-19. It is intentionally repo-wide and includes product code, tests, orchestration surfaces, and governance docs.

## Executive Summary

- The repository is in an early scaffold state with `ACTIVE_PHASE: 0`.
- The only implemented product behavior is the Phase 0 tempo-analysis CLI path.
- Most services and infrastructure components are spec-shaped stubs that intentionally defer real work to later FILE_PLAN rows.
- The repo already had a mature Claude-oriented control plane under `.claude/`, but no Codex-native mirror surface.
- Verification and repair scripts are stronger than the product surface itself; they are the right backend to reuse for the new harness.
- The main control-plane gap before this pass was asymmetry: Codex had `AGENTS.md` but no repo-local agents, skills, or hooks comparable to `.claude/*`.

## Risk Summary

- Product/runtime risk: high. Most core services are placeholders.
- Spec-drift risk: medium. The spec is detailed, while the implemented runtime surface is narrow.
- Agent-ops risk before this pass: medium-high. One orchestration surface existed, the other did not.
- Verification risk: medium. `make status` and other `uv`-backed flows depend on writable cache paths in the execution environment.

## File Inventory

### Governance and root metadata

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `AGENTS.md` | Codex-facing repo instructions | Active | Good baseline rules; lacked a full Codex harness surface. |
| `CLAUDE.md` | Claude build-loop contract | Active | Strongest existing orchestration entrypoint. |
| `README.md` | Human overview and quickstart | Active | Accurate scaffold framing; should now mention dual-surface harness docs. |
| `LICENSE` | MIT license | Stable | No action needed. |
| `Makefile` | Operator shortcuts | Active | Good shared backend entrypoint; suitable place for harness review target. |
| `pyproject.toml` | Package metadata and deps | Active | Phase-based extras are well-scoped. |
| `ruff.toml` | Formatting and lint policy | Active | Clean and minimal. |
| `.pre-commit-config.yaml` | Pre-commit gates | Active | Mirrors verify policy. |
| `.gitignore` | Ignore policy | Active | Correctly ignores `.build/` and `app_data/`. |
| `.python-version` | Python version pin | Stable | Matches project requirements. |
| `uv.lock` | Locked dependency graph | Active | Shared reproducibility surface. |

### Product spec and distilled docs

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `docs/SPEC.md` | Authoritative product spec | Authoritative | Detailed and stable; must remain untouched unless explicitly requested. |
| `docs/ARCHITECTURE.md` | Layering summary | Active | Good distillation of service boundaries. |
| `docs/DATA_MODEL.md` | Data-model summary | Active | Captures confidence and artifact-versioning rules. |
| `docs/PIPELINE.md` | Pipeline summary | Active | Clear analyzer-routing constraints. |
| `docs/build/AGENT_CONTRACT.md` | Shared build-loop contract | New | Frontend-neutral operational contract for Claude and Codex. |
| `docs/AGENT_HARNESS_SPEC.md` | Repo-local harness spec | New | Added to formalize the dual-surface control plane. |
| `docs/REPO_AUDIT.md` | Repo-wide audit | New | Added to satisfy the requested deep repo analysis. |

### Build-plan docs

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `docs/build/PHASES.md` | Phase ceiling and exit criteria | Active | Current active phase is 0. |
| `docs/build/FILE_PLAN.md` | Living file backlog | Active | Product backlog is well-structured and intentionally authoritative. |
| `docs/build/DECISIONS.md` | ADR-lite decisions | Active | Correct place to record harness-priority override. |
| `docs/build/BUILD_LOG.md` | Append-only execution log | Active | Correct place to document this control-plane pass. |

### Claude control plane

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `.claude/settings.json` | Claude permissions and hooks | Active | Most complete existing control-plane config. |
| `.claude/commands/build.md` | Build loop command | Active | Encodes FILE_PLAN-first execution. |
| `.claude/commands/continue.md` | Build alias | Active | Thin alias to build. |
| `.claude/commands/phase.md` | Phase print/promote | Active | Correctly avoids silent phase jumps. |
| `.claude/commands/repair.md` | Repair loop command | Active | Good bounded repair flow. |
| `.claude/commands/replan.md` | Replan proposal flow | Active | Proposal-only behavior is correct. |
| `.claude/commands/status.md` | Status command | Active | Good read-only surface. |
| `.claude/commands/verify.md` | Verify command | Active | Good summarized verification surface. |
| `.claude/agents/build-engineer.md` | Row-scoped implementer | Active | Strong scope discipline. |
| `.claude/agents/mir-domain-expert.md` | MIR/spec reviewer | Active | Useful model for Codex review role. |
| `.claude/agents/planner.md` | Plan-maintenance role | Active | Proposal-first behavior is good. |
| `.claude/agents/repair-engineer.md` | Minimal repair role | Active | Strong repair boundaries. |
| `.claude/agents/verifier.md` | Read-only verification role | Active | Good diagnostic role. |
| `.claude/skills/audio-pipeline.md` | Analyzer guidance | Active | High-signal domain skill. |
| `.claude/skills/mir-confidence-policy.md` | Confidence-policy skill | Active | Cross-cutting and important. |
| `.claude/skills/pyside-ui.md` | UI guidance | Active | Future-facing for Phase 1. |
| `.claude/skills/source-separation.md` | Stem/source skill | Active | Future-facing for Phase 2+. |
| `.claude/skills/vector-search.md` | Similarity/index guidance | Active | Future-facing for similarity work. |
| `.claude/hooks/session_start_bootstrap.sh` | State/bootstrap hook | Active | Good read-only session primer. |
| `.claude/hooks/stop_self_repair.sh` | Verify-and-brief hook | Active | Strong repair trigger; useful compatibility reference. |

### Codex control plane

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `.codex/README.md` | Codex entrypoint and workflow | New | Added in this pass. |
| `.codex/CODEX_AGENT_MAP.md` | Role/delegation map | New | Added in this pass. |
| `.codex/agents/build-engineer.md` | Codex row implementer | New | Mirrors row-scoped discipline. |
| `.codex/agents/harness-reviewer.md` | Repo-control-plane reviewer | New | Added for harness-specific reviews. |
| `.codex/agents/mir-reviewer.md` | MIR/spec reviewer | New | Codex counterpart to Claude MIR role. |
| `.codex/agents/planner.md` | Replan/audit role | New | Proposal-oriented planning role. |
| `.codex/agents/repair-engineer.md` | Minimal repair role | New | Mirrors repair discipline. |
| `.codex/agents/verifier.md` | Read-only verifier | New | Mirrors verification discipline. |
| `.codex/skills/audio-pipeline/SKILL.md` | Audio-analysis skill | New | Shared rules adapted for Codex triggering. |
| `.codex/skills/deep-sound-build-loop/SKILL.md` | Build-loop orchestration skill | New | Added to give Codex a repo-execution entry skill. |
| `.codex/skills/harness-self-review/SKILL.md` | Harness-review skill | New | Added for suggest-only control-plane review. |
| `.codex/skills/harness-maintenance/SKILL.md` | Harness and review skill | New | New repo-control-plane skill. |
| `.codex/skills/mir-confidence-policy/SKILL.md` | Confidence-policy skill | New | Required for probabilistic outputs. |
| `.codex/skills/pyside-ui/SKILL.md` | UI guidance skill | New | Future-facing Phase 1 UI skill. |
| `.codex/skills/source-separation/SKILL.md` | Stem/source skill | New | Future-facing Phase 2+ skill. |
| `.codex/skills/vector-search/SKILL.md` | Similarity/index skill | New | Future-facing Codex guidance. |
| `.codex/hooks/session_start_status.sh` | Status hook | New | Read-only session state surfacing. |
| `.codex/hooks/stop_self_review.sh` | Suggest-only review hook | New | Runs the toolset review script. |

### Shared automation scripts

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `scripts/bootstrap.sh` | Install `uv`, sync dev deps | Active | Good bootstrap path. |
| `scripts/print_build_contract.py` | Shared contract printer | New | Small helper to surface the common operator contract. |
| `scripts/session_start.py` | Shared startup summary | New | Frontend-neutral status bootstrap. |
| `scripts/status.py` | Read-only plan status | Active | Safe before dependency sync; valuable shared backend. |
| `scripts/update_plan.py` | Controlled FILE_PLAN mutator | Active | Correctly serializes writes and enforces the no-direct-edit rule. |
| `scripts/verify.py` | Structured verification runner | Active | Strong shared gate backend. |
| `scripts/repair.py` | Repair-brief generator | Active | Strong failure summarization backend. |
| `scripts/toolset_review.py` | Suggest-only harness review | New | Added for Codex/Claude-compatible control-plane feedback. |

### Runtime package surface

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `src/deep_sound/__init__.py` | Package init/version | Scaffolded | Fine for current phase. |
| `src/deep_sound/cli.py` | Phase 0 CLI entrypoint | Implemented | Only real end-user path today. |
| `src/deep_sound/domain/confidence.py` | Confidence value object | Implemented | One of the strongest completed domain modules. |
| `src/deep_sound/domain/track.py` | Track model | Stub | Spec-shaped, intentionally partial. |
| `src/deep_sound/domain/stem.py` | Stem model | Stub | Correct confidence requirement, no real pipeline yet. |
| `src/deep_sound/domain/source.py` | Source model | Stub | Good type routing groundwork. |
| `src/deep_sound/domain/feature_view.py` | Feature-view model | Stub-plus | Good artifact metadata fields. |
| `src/deep_sound/domain/__init__.py` | Domain package init | Minimal | Pure packaging surface. |
| `src/deep_sound/services/__init__.py` | Services package init | Minimal | Pure packaging surface. |
| `src/deep_sound/services/analysis_service.py` | Analysis orchestrator | Stub | Important future boundary, not yet implemented. |
| `src/deep_sound/services/explanation_service.py` | Explanation surface | Stub | Needed in Phase 1. |
| `src/deep_sound/services/feature_service.py` | Feature storage service | Stub | Next important Phase 0 service dependency chain. |
| `src/deep_sound/services/library_service.py` | Library import surface | Stub | Future Phase 1 work. |
| `src/deep_sound/services/similarity_service.py` | Search/rerank surface | Stub | Important future Phase 0 row. |
| `src/deep_sound/services/source_service.py` | Stem/source service | Stub | Correctly deferred to later phases. |
| `src/deep_sound/infra/__init__.py` | Infra package init | Minimal | Pure packaging surface. |
| `src/deep_sound/infra/audio_decoder.py` | Decode boundary | Stub | Correct spec intent, no implementation yet. |
| `src/deep_sound/infra/analyzers/__init__.py` | Analyzer package init | Minimal | Fine. |
| `src/deep_sound/infra/analyzers/tempo_librosa.py` | Tempo analyzer | Implemented | Current core product capability. |
| `src/deep_sound/infra/index/__init__.py` | Index package init | Minimal | Fine. |
| `src/deep_sound/infra/index/faiss_index.py` | Vector-index boundary | Stub | Correctly gated behind Phase 1. |
| `src/deep_sound/infra/storage/__init__.py` | Storage package init | Minimal | Fine. |
| `src/deep_sound/infra/storage/sqlite_store.py` | SQLite store boundary | Stub | Important future infra row. |

### Tests

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `tests/__init__.py` | Test package init | Minimal | Fine. |
| `tests/conftest.py` | Shared fixtures | Implemented | Strong generated audio fixture strategy. |
| `tests/test_analyze.py` | Tempo CLI/analyzer tests | Implemented | Covers the only real product path. |
| `tests/test_cli.py` | CLI smoke tests | Implemented | Narrow but appropriate. |
| `tests/test_confidence_bands.py` | Confidence boundary tests | Implemented | Good guardrail for a core invariant. |
| `tests/fixtures/README.md` | Fixture policy | Active | Keeps binary fixtures out of git. |

### CI and git-managed metadata

| Path | Purpose | Maturity | Notes |
|---|---|---|---|
| `.github/workflows/ci.yml` | CI verify workflow | Active | Mirrors local verify pipeline. |

## Control-Plane Gaps Found

Before this pass, the main gaps were:

1. No Codex-native skill/agent/hook surface despite explicit Codex usage.
2. No suggest-only self-review path for recommending harness additions.
3. No harness spec documenting when repo-control-plane work may temporarily override normal FILE_PLAN picking.

## Recommended Near-Term Focus

- Finish the Codex harness and keep it thin by reusing `scripts/`.
- Return to the Phase 0 FILE_PLAN chain starting with `P0-014`.
- Keep the repo audit updated only when the control plane changes materially; it should not become a changelog.
