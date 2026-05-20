# Repo Audit

This audit inventories the Deep-Sound repository after the Phase 7 beta acceptance hardening pass on 2026-05-20. It is repo-wide and includes product code, tests, orchestration surfaces, and governance docs.

## Executive Summary

- `ACTIVE_PHASE: 7`; all Phase 0 through Phase 7 rows are complete except this closeout row while this audit is being written.
- The runtime now covers a dependency-light real-library beta path: import, profile analysis, profile indexing, indexed/scan search fallback, hydrated CLI output, source-aware fake-provider analysis, clip/window storage, waveform cache DTOs, and import-safe UI workflow DTO seams.
- Core verification remains intentionally light: no required FAISS, PySide, Demucs, learned embeddings, cloud services, packaging installers, or heavy MIR extras.
- Search and MIR-facing outputs continue to expose confidence/caveats instead of definitive labels.
- `.claude/` and `.codex/` remain dual control-plane surfaces over the same shared scripts.

## Risk Summary

- Product/runtime risk: medium. The beta workflow is usable through CLI/service seams, but full desktop interaction, commercial packaging, and production-quality MIR models remain future work.
- Spec-drift risk: medium. Phase 7 is repo-local build-plan scope layered on top of the spec; its acceptance boundary is documented in `docs/build/PHASES.md` and `docs/build/DECISIONS.md`.
- Dependency risk: low for default gates. Optional FAISS/PySide/Demucs paths remain isolated.
- Data lifecycle risk: medium. Feature reruns are now idempotent for canonical views, but richer migration/retention policy is still future work.
- UI risk: medium. DTO/controller seams are import-safe, but full PySide wiring and manual desktop QA remain incomplete.

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
| UI workflow | DTO seam | `ui/library_workflow.py` maps import/analyze/index/search/progress/warnings/results/feedback DTOs without importing PySide. |

## Key Files Added Or Advanced In Phase 7

| Path | Purpose |
|---|---|
| `src/deep_sound/services/library_analysis_service.py` | Thin profile orchestrator over existing Library/Analysis/Source services. |
| `src/deep_sound/domain/clip.py` | User-selected clip/window domain object. |
| `src/deep_sound/services/waveform_service.py` | Waveform JSON cache artifact writer and clip/waveform DTOs. |
| `src/deep_sound/ui/library_workflow.py` | Import-safe workflow/controller DTO seam. |
| `tests/test_phase7_*.py` | Focused Phase 7 storage, profile, CLI, index, source, clip, waveform, UI, integration, and smoke coverage. |

## Governance And Control Plane

| Path | Status | Notes |
|---|---|---|
| `AGENTS.md` | Active | Codex-facing repo contract; still matches the build-loop rules. |
| `.codex/README.md` | Active | Codex-local entrypoint over shared scripts. |
| `.codex/CODEX_AGENT_MAP.md` | Active | Role/delegation map used by current runs. |
| `.claude/` | Active | Claude-oriented commands/agents/hooks remain available. |
| `docs/AGENT_HARNESS_SPEC.md` | Active | Shared control-plane contract. |
| `docs/build/PHASES.md` | Active | Current phase ceiling and Phase 7 acceptance boundary. |
| `docs/build/FILE_PLAN.md` | Active | Mutated only through `scripts/update_plan.py`. |
| `docs/build/DECISIONS.md` | Active | Records dependency-light phase boundaries through Phase 7. |
| `docs/build/BUILD_LOG.md` | Active | Append-only build history; Phase 7 entries are current. |
| `scripts/toolset_review.py` | Active | Suggest-only review; no auto-edits. |

## Manual QA Checklist

Use a small local folder with at least two valid audio files and one intentionally broken `.wav` text file.

1. Run `deep-sound analyze-library --library-db /tmp/deep-sound-beta.sqlite --import-path <folder> --profile searchable`.
2. Confirm output reports completed tracks, `profile=searchable`, and a nonzero feature count.
3. Run the same analyze command again and confirm it succeeds without duplicate feature errors.
4. Run `deep-sound index-library --library-db /tmp/deep-sound-beta.sqlite --profile searchable`.
5. Confirm rhythm, chroma, MFCC, production, and structure index lines are printed.
6. Pick a query track id from the SQLite library and run `deep-sound search-library --library-db /tmp/deep-sound-beta.sqlite --query-id <id> --mode rhythm --show-titles --explain`.
7. Confirm result rows show title/path metadata, `entity=track`, backend, per-dimension scores, and caveats when a scan fallback is used.
8. Run a `source_aware` analysis on a tiny test library only when fake-provider behavior is desired; do not install Demucs for default QA.
9. Open the generated `app_data/waveforms/*.json` cache in a text viewer and confirm it records track id, version, sample rate, duration, and points.

## Remaining Gaps

- Full PySide desktop workflow wiring is not implemented; DTOs are ready but widgets/controllers need future rows.
- Source-aware acceptance uses fake copied stems for default verification. Real separation quality remains gated behind optional Demucs work.
- Clip search has domain/storage/cache seams but not full audio playback or clip-specific analyzer routing in the UI.
- `scripts/toolset_review.py` is intentionally shallow and suggest-only; it should not be treated as a complete governance audit.

## Closeout Checks

- `python3 scripts/verify.py`
- `python3 scripts/status.py`
- `python3 scripts/toolset_review.py`
