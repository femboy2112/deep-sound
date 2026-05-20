# Repo Audit

This audit inventories the Deep-Sound repository after the Phase 9 interactive desktop beta hardening pass on 2026-05-20. It is repo-wide and includes product code, tests, orchestration surfaces, and governance docs.

## Executive Summary

- `ACTIVE_PHASE: 9`; Phase 9 rows define the interactive desktop beta hardening boundary.
- The runtime now covers a dependency-light desktop beta seam plus interactive wiring DTOs: app/session config, import/analyze/index/search/waveform/clip/feedback controller intents, index/job snapshots, hydrated result cards, source detail DTOs, selected-track waveform/clip state, clip-owned features, and optional PySide widget factories.
- Core verification remains intentionally light: no required FAISS, PySide, Demucs, learned embeddings, cloud services, packaging installers, or heavy MIR extras.
- Search and MIR-facing outputs continue to expose confidence/caveats instead of definitive labels.
- `.claude/` and `.codex/` remain dual control-plane surfaces over the same shared scripts.

## Risk Summary

- Product/runtime risk: medium. The beta workflow is usable through CLI/service seams and controller-backed UI actions, but playback transport, commercial packaging, and production-quality MIR models remain future work.
- Spec-drift risk: medium. Phases 7 through 9 are repo-local build-plan scopes layered on top of the spec; their acceptance boundaries are documented in `docs/build/PHASES.md` and `docs/build/DECISIONS.md`.
- Dependency risk: low for default gates. Optional FAISS/PySide/Demucs paths remain isolated.
- Data lifecycle risk: medium. Feature reruns are now idempotent for canonical views, but richer migration/retention policy is still future work.
- UI risk: medium. Desktop controller and DTO/action seams are import-safe; real installed PySide QA remains optional/manual.

## Current Product Surface

| Area | Status | Notes |
|---|---|---|
| Library import | Active | `LibraryService` imports files/folders, dedupes by hash, records failed imports, and preserves originals. |
| Analysis profiles | Active | `LibraryAnalysisService` supports `minimal`, `searchable`, and `source_aware` profiles. |
| Feature lifecycle | Active | SQLite has feature upsert/replacement APIs, track analysis status updates, and failed-analysis job records. |
| Searchable profile | Active | `searchable` materializes full-mix rhythm/chroma/MFCC plus production texture and structure features. |
| Source-aware profile | Beta seam | Uses `FakeSeparationProvider` in core tests; Demucs remains optional. |
| Indexing | Active | `IndexService.build_profile()` builds profile-matched indexes using FAISS wrapper or NumPy fallback. |
| Search retrieval | Active | `SimilarityService` separates retrieval/rerank, discloses backend, falls back to scans, and filters incompatible source types for source searches. |
| CLI workflow | Active | `analyze-library --profile`, `index-library --profile`, and `search-library --show-titles --explain` cover the beta path. |
| Clip/window | Active | `ClipWindow`, SQLite `clip_windows`, and `ClipAnalysisService` support clip-owned rhythm/harmony/timbre feature rows under app data. |
| Waveform/cache | DTO/service seam | `WaveformService` writes JSON peak/RMS cache artifacts without PySide. |
| UI workflow | Interactive beta seam | `ui/library_workflow.py` maps import/analyze/index/search/progress/warnings/results/waveform/clip/feedback DTOs without importing PySide; `ui/main_window.py` adds controller-backed action binding. |
| Desktop settings | Active | `ui/session_config.py` persists library DB, app data dir, active profile, and last query state. |
| Result inspection | Active | Result cards retain backend, stale-index warnings, caveats, dimension scores, preview/compare metadata, and feedback action intents. |
| Source detail | Active | Source graph/detail DTOs expose confidence, compatible source search actions, correction gating, and correction metadata. |

## Key Files Added Or Advanced In Phase 9

| Path | Purpose |
|---|---|
| `src/deep_sound/ui/main_window.py` | Import-safe controller action binder plus optional PySide main-window signal wiring. |
| `src/deep_sound/ui/library_workflow.py` | Richer workflow progress stage DTOs and retry action metadata. |
| `src/deep_sound/ui/track_detail.py` | Selected-track detail data with waveform panel and clip selection state. |
| `src/deep_sound/services/clip_analysis_service.py` | Clip-owned feature materialization under app data without modifying originals. |
| `src/deep_sound/ui/query_builder.py` | Interactive track/clip/source query validation and search-intent readiness. |
| `src/deep_sound/ui/results_view.py` | Preview, compare, relevant, and irrelevant action DTOs for result cards. |
| `src/deep_sound/ui/source_graph.py` | Source selection detail, correction gating, and compatible source-search action DTOs. |
| `tests/test_phase9_*.py` | Focused dependency-light Phase 9 tests plus optional PySide skip smoke. |

## Governance And Control Plane

| Path | Status | Notes |
|---|---|---|
| `AGENTS.md` | Active | Codex-facing repo contract; still matches the build-loop rules. |
| `.codex/README.md` | Active | Codex-local entrypoint over shared scripts. |
| `.codex/CODEX_AGENT_MAP.md` | Active | Role/delegation map used by current runs. |
| `.claude/` | Active | Claude-oriented commands/agents/hooks remain available. |
| `docs/AGENT_HARNESS_SPEC.md` | Active | Shared control-plane contract. |
| `docs/build/PHASES.md` | Active | Current phase ceiling and Phase 9 interactive desktop beta boundary. |
| `docs/build/FILE_PLAN.md` | Active | Mutated only through `scripts/update_plan.py`. |
| `docs/build/DECISIONS.md` | Active | Records dependency-light phase boundaries through Phase 8; Phase 9 boundary is in `PHASES.md`. |
| `docs/build/BUILD_LOG.md` | Active | Append-only build history; Phase 9 closeout is current when P9-015 completes. |
| `scripts/toolset_review.py` | Active | Suggest-only review; no auto-edits. |

## Manual QA Checklist

See `docs/desktop_beta_manual_qa.md` for the Phase 9 desktop beta checklist. It covers service workflow, waveform/clip state, clip-owned feature materialization, result/source actions, feedback, and optional PySide smoke steps.

## Remaining Gaps

- Source-aware acceptance uses fake copied stems for default verification. Real separation quality remains gated behind optional Demucs work.
- Playback transport remains a UI placeholder.
- `scripts/toolset_review.py` is intentionally shallow and suggest-only; it should not be treated as a complete governance audit.

## Closeout Checks

- `python3 scripts/verify.py`
- `python3 scripts/status.py`
- `python3 scripts/toolset_review.py`
