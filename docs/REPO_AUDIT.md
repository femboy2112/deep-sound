# Repo Audit

This audit inventories the Deep-Sound repository during the Phase 15 beta testing and usability campaign on 2026-05-21. It is repo-wide and includes product code, tests, orchestration surfaces, and governance docs.

## Executive Summary

- `ACTIVE_PHASE: 15`; Phase 15 rows define the beta campaign runner, report contract metadata, `quality` profile indexing/search coverage, manual usability scenario reporting, and low-risk UI usability states.
- The runtime now covers a dependency-light desktop beta seam plus interactive wiring DTOs: app/session config, import/analyze/index/search/waveform/clip/feedback controller intents, index/job snapshots, hydrated result cards, source detail DTOs, selected-track waveform/clip state, clip-owned features, and optional PySide widget factories.
- `source_aware` remains the fake-provider route; `source_aware_real` is the explicit Demucs-backed opt-in path.
- `scripts/live_qa.py --fixture-mode generated --real-smoke-policy auto --playback-smoke-policy auto` records required generated-fixture workflow evidence and runs installed PySide/Demucs/playback smoke when available.
- `scripts/beta_campaign.py --fixture-mode generated --real-smoke-policy off --playback-smoke-policy off` records the required Phase 15 evidence bundle in `.build/beta_campaign_report.*`.
- `scripts/mir_quality_eval.py --fixture-mode generated --strict` records required deterministic MIR quality evidence in `.build/mir_quality_report.*`.
- The `[playback]` extra adds `sounddevice` for explicitly enabled local output; default verification does not open audio devices.
- The `[demucs]` extra now pins `torch` and `torchaudio` to uv's explicit `pytorch-cpu` index. CUDA/NVIDIA/Triton packages are not part of the default CPU Demucs path.
- Core verification remains intentionally light: no required FAISS, PySide, Demucs, learned embeddings, cloud services, packaging installers, or heavy MIR extras.
- Search and MIR-facing outputs continue to expose confidence/caveats instead of definitive labels.
- `.claude/` and `.codex/` remain dual control-plane surfaces over the same shared scripts.

## Risk Summary

- Product/runtime risk: medium. The beta workflow is usable through CLI/service seams and controller-backed UI actions, playback has a guarded beta transport, and deterministic MIR quality evidence now has a generated-fixture harness; commercial packaging and production-quality learned MIR models remain future work.
- Spec-drift risk: medium. Phases 7 through 9 are repo-local build-plan scopes layered on top of the spec; their acceptance boundaries are documented in `docs/build/PHASES.md` and `docs/build/DECISIONS.md`.
- Dependency risk: low for default gates. Optional FAISS/PySide/Demucs paths remain isolated, and default Demucs resolution is CPU-only.
- Data lifecycle risk: medium. Feature reruns are now idempotent for canonical views, but richer migration/retention policy is still future work.
- UI risk: medium. Desktop controller and DTO/action seams are import-safe; real installed PySide QA remains optional/manual and is reported as a separate live QA gate.

## Current Product Surface

| Area | Status | Notes |
|---|---|---|
| Library import | Active | `LibraryService` imports files/folders, dedupes by hash, records failed imports, and preserves originals. |
| Analysis profiles | Active | `LibraryAnalysisService` supports `minimal`, `searchable`, dependency-light `quality`, `source_aware`, and explicit opt-in `source_aware_real` profiles. |
| Feature lifecycle | Active | SQLite has feature upsert/replacement APIs, track analysis status updates, and failed-analysis job records. |
| Searchable profile | Active | `searchable` materializes full-mix rhythm/chroma/MFCC plus production texture and structure features. |
| Source-aware profile | Beta seam | `source_aware` uses `FakeSeparationProvider` in core tests; `source_aware_real` uses `DemucsProvider` and fails clearly when Demucs is absent. |
| Indexing | Active | `IndexService.build_profile()` builds profile-matched indexes using FAISS wrapper or NumPy fallback and records unavailable profile dimensions as explicit scan caveats instead of aborting the whole profile. |
| Search retrieval | Active | `SimilarityService` separates retrieval/rerank, discloses backend, falls back to scans, and filters incompatible source types for source searches. |
| CLI workflow | Active | `analyze-library --profile`, `index-library --profile`, and `search-library --show-titles --explain` cover the beta path; `--profile source_aware_real` is the opt-in real-source smoke route. |
| Clip/window | Active | `ClipWindow`, SQLite `clip_windows`, and `ClipAnalysisService` support clip-owned rhythm/harmony/timbre feature rows under app data. |
| Waveform/cache | DTO/service seam | `WaveformService` writes JSON peak/RMS cache artifacts without PySide. |
| UI workflow | Interactive beta seam | `ui/library_workflow.py` maps import/analyze/index/search/progress/warnings/results/waveform/clip/feedback/playback DTOs without importing PySide; `ui/main_window.py` adds controller-backed action binding. |
| Playback | Beta transport | `PlaybackService` stays inspection-safe by default; `LocalPlaybackAdapter(audio_output_enabled=True)` uses `soundfile`/`sounddevice`, clamps seeks, stops output, and reports device/decode errors as failed state. |
| MIR quality evidence | Active | `scripts/mir_quality_eval.py` runs generated-fixture checks for tempo, chord/chroma, melody contour, drum groove, bass motion, source routing, and confidence bounds. |
| Beta campaign evidence | Active | `scripts/beta_campaign.py` aggregates verify, generated live QA, strict MIR quality, strict repo dive, and toolset-review evidence with report contract metadata. |
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

## Key Files Added Or Advanced In Phase 10

| Path | Purpose |
|---|---|
| `src/deep_sound/infra/separation/providers.py` | Demucs availability, output validation, and opt-in error handling. |
| `src/deep_sound/services/library_analysis_service.py` | Adds `source_aware_real` routing while preserving the fake-provider `source_aware` default. |
| `src/deep_sound/cli.py` | Exposes `source_aware_real` plus `--demucs-executable` for optional real-source smoke. |
| `tests/test_phase10_*.py` | Dependency-light fake-Demucs contract, CLI, artifact-safety, and skip-safe optional smoke coverage. |

## Key Files Added Or Advanced In Phase 11

| Path | Purpose |
|---|---|
| `scripts/live_qa.py` | Non-mutating generated-fixture live QA harness that writes `.build/live_qa_report.json` and `.build/live_qa_report.md`. |
| `tests/test_phase11_live_qa_script.py` | Focused coverage for required generated-fixture report output and optional-gate skip reporting. |
| `docs/desktop_beta_manual_qa.md` | Phase 11 live evidence checklist and known-failure logging standard. |

## Key Files Added Or Advanced In Phase 12

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | CPU-only Torch/Torchaudio source pinning for the `[demucs]` extra. |
| `scripts/live_qa.py` | `auto|required|off` real-smoke policy plus generated Demucs smoke fixture support. |
| `tests/test_phase12_live_qa_policy.py` | Focused policy coverage for auto, required, and off modes. |
| `tests/test_phase12_optional_extra_resolution.py` | Lockfile/config guard against CUDA/NVIDIA/Triton packages in the CPU Demucs path. |

## Key Files Added Or Advanced In Phase 13

| Path | Purpose |
|---|---|
| `pyproject.toml` / `uv.lock` | Optional `[playback]` extra for `sounddevice`, excluded from default, `[ui]`, and `[demucs]`. |
| `src/deep_sound/services/playback_service.py` | Import-safe `PlaybackTransport` protocol plus real local output stop/seek/error handling. |
| `src/deep_sound/ui/library_workflow.py` | Controller playback transport routing, stop intent, and snapshot playback state. |
| `src/deep_sound/ui/track_detail.py` / `src/deep_sound/ui/main_window.py` | PySide playback buttons and state display routed through controller callbacks. |
| `scripts/live_qa.py` | `--run-playback-smoke` plus `--playback-smoke-policy auto|required|off`. |
| `tests/test_phase13_*.py` | Focused playback service, controller, PySide control, live QA policy, and opt-in real playback smoke coverage. |

## Key Files Added Or Advanced In Phase 14

| Path | Purpose |
|---|---|
| `scripts/mir_quality_eval.py` | Dependency-light generated-fixture MIR quality harness with JSON/Markdown reports. |
| `src/deep_sound/services/library_analysis_service.py` | Adds the `quality` profile over existing deterministic services and fake-provider source routing. |
| `src/deep_sound/infra/analyzers/source_chords.py` | Chroma-change-aware segmentation, adjacent duplicate merge, stable reference root, and calibrated confidence. |
| `src/deep_sound/infra/analyzers/melody_contour.py` | Bounded pitch-band contour, energy gating, smoothing, voicing, smoothness, and low-confidence behavior. |
| `src/deep_sound/infra/analyzers/bass_stem.py` / `src/deep_sound/infra/analyzers/drum_stem.py` | Additional normalized bass/drum quality descriptors while preserving existing stat keys. |
| `src/deep_sound/services/analysis_service.py` | Persists upgraded analyzer versions and richer source-timbre quality stats. |
| `src/deep_sound/services/similarity_service.py` / `src/deep_sound/services/explanation_service.py` | Quality search regression surface and confidence-language guardrails. |
| `tests/test_phase14_*.py` / `tests/test_mir_quality_eval.py` | Focused generated-fixture, profile, analyzer, search, and confidence-language coverage. |

## Key Files Added Or Advanced In Phase 15

| Path | Purpose |
|---|---|
| `scripts/report_contracts.py` | Shared schema, environment, dependency-policy, skip, and follow-up metadata helpers for generated reports. |
| `scripts/beta_campaign.py` | Phase 15 campaign runner that aggregates verify, live QA, MIR quality, repo dive, and toolset review evidence. |
| `scripts/live_qa.py` | Adds Phase 15 report metadata and manual usability task results while preserving optional-gate policy semantics. |
| `scripts/mir_quality_eval.py` | Adds Phase 15 report metadata to generated quality evidence. |
| `src/deep_sound/services/index_service.py` | Adds `quality` profile indexing and unavailable-dimension caveats. |
| `src/deep_sound/ui/main_window.py` | Adds import-safe usability state DTOs, action gating, empty/error state labels, and deterministic widget object names. |
| `tests/test_phase15_*.py` / `tests/test_beta_campaign.py` | Focused campaign, report-contract, quality indexing/workflow, manual usability, and UI state coverage. |

## Governance And Control Plane

| Path | Status | Notes |
|---|---|---|
| `AGENTS.md` | Active | Codex-facing repo contract; still matches the build-loop rules. |
| `.codex/README.md` | Active | Codex-local entrypoint over shared scripts. |
| `.codex/CODEX_AGENT_MAP.md` | Active | Role/delegation map used by current runs. |
| `.claude/` | Active | Claude-oriented commands/agents/hooks remain available. |
| `docs/AGENT_HARNESS_SPEC.md` | Active | Shared control-plane contract. |
| `docs/build/PHASES.md` | Active | Current phase ceiling and Phase 15 beta testing/usability boundary. |
| `docs/build/FILE_PLAN.md` | Active | Mutated only through `scripts/update_plan.py`. |
| `docs/build/DECISIONS.md` | Active | Records dependency-light phase boundaries through Phase 15. |
| `docs/build/BUILD_LOG.md` | Active | Append-only build history; Phase 15 closeout is current when P15-010 completes. |
| `scripts/toolset_review.py` | Active | Suggest-only review; no auto-edits. |

## Manual QA Checklist

See `docs/desktop_beta_manual_qa.md` for the Phase 15 desktop beta checklist. It covers the beta campaign runner, generated-fixture live QA evidence, generated MIR quality evidence, service workflow, quality profile indexing, waveform/clip state, clip-owned feature materialization, result/source actions, feedback, optional PySide smoke steps, CPU real-Demucs smoke steps, and optional playback smoke steps.

## Remaining Gaps

- Source-aware acceptance uses fake copied stems for default verification. CPU real separation is smoke-testable through `source_aware_real`, but GPU acceleration, real-separation quality tuning, and broad corpus validation remain future work.
- Playback transport is beta-grade and guarded; broader UX polish, device selection, and packaging remain future work.
- The live QA harness proves generated-fixture workflow repeatability; broader human-curated corpus quality remains manual beta evidence.
- The MIR quality harness proves generated-fixture deterministic analyzer behavior; broad-corpus quality, real separation quality, and learned-model MIR remain future work.
- `scripts/toolset_review.py` is intentionally shallow and suggest-only; it should not be treated as a complete governance audit.

## Closeout Checks

- `python3 scripts/verify.py`
- `python3 scripts/beta_campaign.py --fixture-mode generated --real-smoke-policy off --playback-smoke-policy off`
- `python3 scripts/mir_quality_eval.py --fixture-mode generated --strict`
- `python3 scripts/live_qa.py --fixture-mode generated --real-smoke-policy auto --playback-smoke-policy auto`
- `QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke --run-demucs-smoke --run-playback-smoke --real-smoke-policy required --playback-smoke-policy required`
- `python3 scripts/status.py`
- `python3 scripts/toolset_review.py`
