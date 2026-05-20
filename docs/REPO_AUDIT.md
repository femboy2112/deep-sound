# Repo Audit

This audit inventories the Deep-Sound repository after the Phase 8 desktop beta workflow integration pass on 2026-05-20. It is repo-wide and includes product code, tests, orchestration surfaces, and governance docs.

## Executive Summary

- `ACTIVE_PHASE: 8`; Phase 8 rows define the desktop beta integration boundary.
- The runtime now covers a dependency-light desktop beta seam: app/session config, import/analyze/index/search/waveform/clip/feedback controller intents, index/job snapshots, hydrated result cards, source detail DTOs, and optional PySide widget factories.
- Core verification remains intentionally light: no required FAISS, PySide, Demucs, learned embeddings, cloud services, packaging installers, or heavy MIR extras.
- Search and MIR-facing outputs continue to expose confidence/caveats instead of definitive labels.
- `.claude/` and `.codex/` remain dual control-plane surfaces over the same shared scripts.

## Risk Summary

- Product/runtime risk: medium. The beta workflow is usable through CLI/service seams, but full desktop interaction, commercial packaging, and production-quality MIR models remain future work.
- Spec-drift risk: medium. Phase 7 is repo-local build-plan scope layered on top of the spec; its acceptance boundary is documented in `docs/build/PHASES.md` and `docs/build/DECISIONS.md`.
- Dependency risk: low for default gates. Optional FAISS/PySide/Demucs paths remain isolated.
- Data lifecycle risk: medium. Feature reruns are now idempotent for canonical views, but richer migration/retention policy is still future work.
- UI risk: medium. Desktop controller and DTO seams are import-safe; real interactive PySide QA remains optional/manual.

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
| Clip/window | Storage seam | `ClipWindow` and SQLite `clip_windows` support clip-owned feature rows. |
| Waveform/cache | DTO/service seam | `WaveformService` writes JSON peak/RMS cache artifacts without PySide. |
| UI workflow | Desktop beta seam | `ui/library_workflow.py` maps import/analyze/index/search/progress/warnings/results/waveform/clip/feedback DTOs without importing PySide. |
| Desktop settings | Active | `ui/session_config.py` persists library DB, app data dir, active profile, and last query state. |
| Result inspection | Active | Result cards retain backend, stale-index warnings, caveats, dimension scores, and feedback action metadata. |
| Source detail | Active | Source graph/detail DTOs expose confidence, compatible source search controls, and correction metadata. |

## Key Files Added Or Advanced In Phase 8

| Path | Purpose |
|---|---|
| `src/deep_sound/ui/session_config.py` | Import-safe desktop session config persistence. |
| `src/deep_sound/ui/library_workflow.py` | `DesktopWorkflowController` over existing services plus job/result/clip/waveform DTOs. |
| `src/deep_sound/ui/waveform_panel.py` | Waveform render DTOs and clip selection panel data. |
| `src/deep_sound/ui/query_builder.py` | Track/clip/source desktop query state mapping. |
| `src/deep_sound/ui/results_view.py` | Backend/caveat/stale warning and feedback action metadata for result cards. |
| `src/deep_sound/ui/source_graph.py` | Source detail DTOs with correction and compatible search controls. |
| `docs/desktop_beta_manual_qa.md` | Manual desktop beta QA checklist. |
| `tests/test_phase8_*.py` | Focused dependency-light desktop workflow tests plus optional PySide skip smoke. |

## Governance And Control Plane

| Path | Status | Notes |
|---|---|---|
| `AGENTS.md` | Active | Codex-facing repo contract; still matches the build-loop rules. |
| `.codex/README.md` | Active | Codex-local entrypoint over shared scripts. |
| `.codex/CODEX_AGENT_MAP.md` | Active | Role/delegation map used by current runs. |
| `.claude/` | Active | Claude-oriented commands/agents/hooks remain available. |
| `docs/AGENT_HARNESS_SPEC.md` | Active | Shared control-plane contract. |
| `docs/build/PHASES.md` | Active | Current phase ceiling and Phase 8 desktop beta boundary. |
| `docs/build/FILE_PLAN.md` | Active | Mutated only through `scripts/update_plan.py`. |
| `docs/build/DECISIONS.md` | Active | Records dependency-light phase boundaries through Phase 8. |
| `docs/build/BUILD_LOG.md` | Active | Append-only build history; Phase 8 entries are current. |
| `scripts/toolset_review.py` | Active | Suggest-only review; no auto-edits. |

## Manual QA Checklist

See `docs/desktop_beta_manual_qa.md` for the Phase 8 desktop beta checklist. It covers service workflow, waveform/clip state, result inspection, feedback, and optional PySide smoke steps.

## Remaining Gaps

- Full interactive PySide signal/slot wiring remains a manual/optional follow-up beyond the import-safe controller seam.
- Source-aware acceptance uses fake copied stems for default verification. Real separation quality remains gated behind optional Demucs work.
- Clip search has selection/query metadata seams but not full clip-specific analyzer routing or playback.
- `scripts/toolset_review.py` is intentionally shallow and suggest-only; it should not be treated as a complete governance audit.

## Closeout Checks

- `python3 scripts/verify.py`
- `python3 scripts/status.py`
- `python3 scripts/toolset_review.py`
