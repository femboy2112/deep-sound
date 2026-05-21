# Repo Dive

Durable summary for the history-backed harness pass. The generated evidence lives in `.build/repo_dive_report.json` and `.build/repo_dive_report.md`; this file records the curated findings that should survive `.build/` cleanup.

## Current Snapshot

- Command: `python3 scripts/repo_dive.py --strict`
- Result: 9 detectors, 0 strict failures.
- Repo state: `ACTIVE_PHASE: 13`, `FILE_PLAN` has 186 `DONE` rows, no repair brief.
- Git history inspected: 24 commits on `claude/ai-repo-setup-framework-E1sbk`.
- Fix/stabilization commits found: 6.
- Watch items: service-boundary hotspots and history-fix follow-up coverage.

## Historical Failures Encoded

| Failure | Evidence | Current prevention |
|---|---|---|
| `docs/build/` hidden by unanchored ignore pattern | `611a6cb fix(gitignore): anchor build/ and dist/ to repo root` | `repo_dive` detects unanchored `build/` or `dist/`; tests cover the detector. |
| Real Demucs smoke used invalid `--two-stems none` | `63b11ab fix: run real demucs smoke path` | `repo_dive` checks that the provider does not reintroduce `--two-stems`; regression tests exercise the detector. |
| Real Demucs smoke needed `torchcodec` | Phase 12 dependency stabilization and `[demucs]` extra updates | `repo_dive` checks `[demucs]` includes `torchcodec` and CPU Torch/Torchaudio guards. |
| CPU real-smoke lockfile could drift into CUDA packages | `815481f test: stabilize CPU real smoke` | `repo_dive` checks `uv.lock` for NVIDIA/CUDA/Triton package names and preserves explicit `pytorch-cpu` source checks. |
| Optional live gates could blur skip/fail semantics | Phase 12/13 live QA policy tests | `repo_dive` checks `auto|required|off`, skip-vs-fail reporting, and Demucs/PySide/playback flags. |
| Playback smoke could become a default dependency | `184a8f4 feat: add guarded real playback transport beta` | `repo_dive` checks playback remains policy-gated; `optional-gate-policy` documents the boundary. |

## Detector Registry

The script uses a small detector registry so future checks can be added without rewriting the report generator.

- `ignored_control_plane`
- `optional_dependency_drift`
- `real_smoke_contract`
- `pyside_import_boundary`
- `artifact_safety`
- `confidence_language`
- `stale_index_correction`
- `service_boundary_hotspot`
- `history_fix_followup`

## High-Churn Areas

The first report flags these as watch-only review targets before future phases expand them:

- `src/deep_sound/services/similarity_service.py`
- `src/deep_sound/ui/results_view.py`
- `src/deep_sound/infra/storage/sqlite_store.py`
- `src/deep_sound/ui/source_graph.py`
- `src/deep_sound/services/source_service.py`
- `src/deep_sound/services/analysis_service.py`
- `src/deep_sound/ui/library_workflow.py`
- `src/deep_sound/services/index_service.py`

These are not failing surfaces. They are places where future work should request focused review because history shows repeated edits across similarity, storage, UI DTOs, source services, indexing, and controller boundaries.

## New Harness Surfaces

- `scripts/repo_dive.py`: stdlib-only read-only audit command.
- `.codex/skills/history-dive/SKILL.md`: use before broad harness or closeout history analysis.
- `.codex/skills/optional-gate-policy/SKILL.md`: use before dependency, smoke-gate, Demucs, PySide, playback, or lockfile changes.
- `.codex/agents/history-auditor.md` and `.claude/agents/history-auditor.md`: read-only history and failure-mode clustering.
- `.codex/agents/dependency-gate-auditor.md` and `.claude/agents/dependency-gate-auditor.md`: read-only optional extras and smoke-gate review.
- `scripts/toolset_review.py`: now consumes `.build/repo_dive_report.json` when present and keeps recommendations suggest-only.

## Future Needs

- Add future FILE_PLAN review rows before expanding high-churn service/UI/storage/search areas.
- Keep Plan-Id trailer coverage visible; initial history inspection found 4 commits without a Plan-Id trailer.
- Run `python3 scripts/repo_dive.py --strict` before broad harness changes, optional dependency changes, or a phase-closeout handoff.
- Run `python3 scripts/toolset_review.py` after `repo_dive` when recommendations should include history-backed evidence.
