# Build Log

Append-only journal of build sessions. Newest entries at the top.

---

## 2026-05-20 — Phase 12 CPU-only real smoke stabilization

- **Agent:** Codex
- **Scope:** Open Phase 12, make Demucs installs CPU-only by default, and make live QA real-smoke policy explicit.
- **Rows touched:** P12-001 .. P12-009.
- **Changes:**
  - Promoted `ACTIVE_PHASE` to 12 and documented the CPU real-smoke boundary in phase and decision docs.
  - Added `torchaudio` to `[demucs]` and pinned `torch`/`torchaudio` to uv's explicit `pytorch-cpu` index.
  - Refreshed `uv.lock`; CUDA/NVIDIA/Triton packages were removed from the default Demucs resolution.
  - Added `scripts/live_qa.py --real-smoke-policy auto|required|off`, generated Demucs fixture support, offscreen PySide handling, and Phase 11 real-Demucs workflow routing.
  - Added Phase 12 tests for live QA policy behavior and optional-extra CPU lockfile/config guards.
  - Refreshed README, manual QA, repo audit, and decisions for CPU-only real-smoke closeout.
- **Verification:**
  - `env UV_CACHE_DIR=/tmp/uv-cache uv lock`
  - `env UV_CACHE_DIR=/tmp/uv-cache uv sync --extra ui --extra demucs`
  - `uv run pytest tests/test_phase11_live_qa_script.py tests/test_phase12_live_qa_policy.py tests/test_phase12_optional_extra_resolution.py tests/test_phase11_live_demucs_workflow.py -q`
  - `uv run pytest tests/test_demucs_provider.py tests/test_phase10_demucs_provider_contract.py tests/test_phase11_live_qa_script.py tests/test_phase12_live_qa_policy.py tests/test_phase12_optional_extra_resolution.py -q`
  - `env UV_CACHE_DIR=/tmp/uv-cache QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke --run-demucs-smoke --real-smoke-policy required`
  - `env UV_CACHE_DIR=/tmp/uv-cache DEEP_SOUND_RUN_DEMUCS_SMOKE=1 uv run pytest tests/test_phase11_live_demucs_workflow.py -vv`
  - `python3 scripts/verify.py`
- **Notes:**
  - Default verification remains dependency-light.
  - Required real-smoke gates needed network/cache access to download Demucs model weights; once available, PySide and real Demucs smoke both passed.
  - GPU/CUDA Demucs support is explicitly future work.

---

## 2026-05-20 — Phase 11 live beta QA hardening

- **Agent:** Codex
- **Scope:** Open Phase 11 and add repeatable live beta QA evidence.
- **Rows touched:** P11-001 .. P11-012.
- **Changes:**
  - Promoted `ACTIVE_PHASE` to 11 and documented the live beta QA boundary in phase and decision docs.
  - Added `scripts/live_qa.py`, a generated-fixture harness that records required import/analyze/index/search/waveform/clip/feedback/artifact-safety gates plus optional Demucs/PySide skip or failure evidence in `.build/live_qa_report.{json,md}`.
  - Added an import-safe playback service seam plus track-detail and controller playback intent DTOs.
  - Added Phase 11 focused tests for playback, track-detail playback controls, controller live metadata, generated live QA reports, live searchable workflow, optional real-Demucs smoke, and optional PySide smoke.
  - Refreshed README, manual QA, repo audit, and decisions for the Phase 11 live evidence standard.
- **Verification:**
  - `uv run pytest tests/test_phase11_playback_service.py tests/test_phase11_track_detail_playback.py tests/test_phase9_track_detail.py tests/test_phase11_controller_live_workflow.py tests/test_phase9_acceptance_controller.py tests/test_phase11_live_qa_script.py tests/test_phase11_live_searchable_workflow.py tests/test_phase11_live_demucs_workflow.py tests/test_phase11_optional_pyside_live_smoke.py`
  - `python3 scripts/live_qa.py --fixture-mode generated`
  - `DEEP_SOUND_RUN_DEMUCS_SMOKE=1 DEEP_SOUND_DEMUCS_EXECUTABLE=/home/leah/ds/deep-sound/.venv/bin/demucs DEEP_SOUND_DEMUCS_SMOKE_AUDIO=/tmp/deep_sound_live_smoke.wav uv run pytest tests/test_phase11_live_demucs_workflow.py -vv`
  - `QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke`
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`
- **Notes:**
  - Real Demucs smoke passed with the local executable and fixture before the later UI-extra sync pruned the Demucs environment.
  - PySide was installed and the offscreen live QA PySide app/window smoke passed.

---

## 2026-05-20 — Phase 10 optional real-source smoke

- **Agent:** Codex
- **Scope:** Open Phase 10 and add an explicit Demucs-backed smoke path while preserving dependency-light defaults.
- **Rows touched:** P10-001 .. P10-010 → DONE.
- **Changes:**
  - Added Phase 10 plan rows through `scripts/update_plan.py` and promoted `ACTIVE_PHASE` to 10.
  - Added `source_aware_real` as the explicit Demucs-backed analysis profile; existing `source_aware` remains fake-provider based.
  - Hardened `DemucsProvider` availability checks, missing/empty stem validation, and opt-in error messages.
  - Exposed `analyze-library --profile source_aware_real` plus `--demucs-executable` for local smoke tests.
  - Added dependency-light fake-Demucs tests for provider contract, CLI routing, artifact safety, and optional smoke skip behavior.
  - Refreshed manual QA, README, repo audit, and decision docs for the real-source boundary.
- **Verification:**
  - `uv run pytest tests/test_demucs_provider.py tests/test_phase10_demucs_provider_contract.py tests/test_phase10_source_aware_real_profile.py tests/test_phase10_cli_real_source.py tests/test_phase10_source_artifact_safety.py tests/test_phase10_optional_demucs_smoke.py tests/test_phase7_source_aware_profile.py tests/test_phase7_cli_profiles.py`
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`
- **Notes:**
  - Optional real Demucs smoke skipped by default unless `DEEP_SOUND_RUN_DEMUCS_SMOKE=1`, a Demucs executable, and `DEEP_SOUND_DEMUCS_SMOKE_AUDIO` are supplied.
  - Default verification still does not require Demucs, PySide, FAISS, learned embeddings, cloud services, installers, or heavy MIR extras.

### Live-smoke follow-up

- **Trigger:** User requested live testing instead of accepting skipped optional smoke.
- **Findings:**
  - Real Demucs rejected the adapter command because `--two-stems none` is invalid for the selected model.
  - The current CPU Torch/Torchaudio stack also requires `torchcodec` for `torchaudio.load`.
- **Fixes:**
  - Removed `--two-stems none` so Demucs runs normal four-stem separation.
  - Added `torchcodec>=0.12` to the `[demucs]` extra and lockfile.
- **Verification:**
  - `DEEP_SOUND_RUN_DEMUCS_SMOKE=1 DEEP_SOUND_DEMUCS_EXECUTABLE=/home/leah/ds/deep-sound/.venv/bin/demucs DEEP_SOUND_DEMUCS_SMOKE_AUDIO=/tmp/deep_sound_live_smoke.wav uv run pytest tests/test_phase10_optional_demucs_smoke.py -vv`
  - `uv run pytest tests/test_phase10_demucs_provider_contract.py tests/test_phase10_optional_demucs_smoke.py`
  - `python3 scripts/verify.py`

---

## 2026-05-20 — Phase 9 interactive desktop beta hardening

- **Agent:** Codex
- **Scope:** Wire interactive desktop beta actions and harden clip/query/result/source UI seams while keeping default verification dependency-light.
- **Rows touched:** P9-004, P9-006 .. P9-015 → DONE.
- **Changes:**
  - Added controller-backed main-window action binding for import, analyze, index, refresh, selected-track search, and row selection.
  - Added richer desktop workflow progress stage DTOs and retry action metadata for import/analyze/index/waveform/feedback jobs.
  - Added selected-track detail data with waveform panel and clip selection state.
  - Added `ClipAnalysisService` to materialize clip-owned rhythm, harmony, and timbre feature views under app data without modifying original audio.
  - Added interactive query validation, result preview/compare/feedback actions, and source graph selection/correction/source-search actions.
  - Added optional PySide smoke coverage that skips when `[ui]` is unavailable.
  - Refreshed manual QA, README status, and repo audit for Phase 9.
- **Verification:**
  - `uv run pytest tests/test_phase9_main_window_actions.py tests/test_phase8_ui_models.py tests/test_phase9_desktop_app.py`
  - `uv run pytest tests/test_phase9_job_progress.py tests/test_phase8_desktop_controller.py tests/test_phase9_acceptance_controller.py`
  - `uv run pytest tests/test_phase9_track_detail.py tests/test_phase8_waveform_panel.py`
  - `uv run pytest tests/test_phase9_clip_analysis.py`
  - `uv run pytest tests/test_phase9_query_builder.py tests/test_phase8_ui_models.py`
  - `uv run pytest tests/test_phase9_results_view.py tests/test_phase8_result_cards.py`
  - `uv run pytest tests/test_phase9_source_graph.py tests/test_phase8_source_detail.py`
  - `uv run pytest tests/test_phase9_optional_pyside_smoke.py`
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`
- **Notes:**
  - Optional PySide smoke skipped in this environment because the `[ui]` extra is not installed.
  - Core verification remains dependency-light and does not require FAISS, PySide, Demucs, learned embeddings, cloud services, installers, or heavy MIR extras.

---

## 2026-05-20 — Phase 8 desktop beta workflow integration

- **Agent:** Codex
- **Scope:** Open Phase 8 and wire dependency-light desktop beta workflow seams.
- **Rows touched:** P8-001 .. P8-014.
- **Changes:**
  - Added Phase 8 plan rows and promoted `ACTIVE_PHASE` to 8 with a desktop-beta boundary decision.
  - Added import-safe desktop session config persistence.
  - Added `DesktopWorkflowController` over existing library, analysis, index, similarity, waveform, and correction services.
  - Added persisted job DTO mapping for import/analyze/index/waveform/feedback controller flows.
  - Added waveform panel DTOs, clip selection/query metadata, track/clip/source query state, result feedback action data, and source detail DTOs.
  - Kept PySide optional by isolating imports to widget factories and adding an optional skip smoke test.
  - Tightened stale-index fingerprinting and source-compatible search filtering to account for feature-value and source-correction changes.
  - Refreshed README, AGENTS phase wording, REPO_AUDIT, and desktop manual QA docs.
- **Verification:**
  - `uv run pytest tests/test_phase8_session_config.py tests/test_phase8_ui_models.py tests/test_phase8_result_cards.py tests/test_phase8_waveform_panel.py tests/test_phase8_source_detail.py tests/test_phase8_desktop_controller.py`

## 2026-05-20 — Phase 7 user-facing beta acceptance hardening

- **Agent:** Codex
- **Scope:** Implement dependency-light beta acceptance workflow hardening.
- **Rows touched:** P7-003 .. P7-015 → DONE.
- **Changes:**
  - Added rerun-safe SQLite feature lifecycle APIs, track analysis status updates, and failed-analysis job recording.
  - Added `LibraryAnalysisService` for `minimal`, `searchable`, and `source_aware` profiles.
  - Wired CLI profile analysis/indexing and hydrated search output with entity/backend/dimension/caveat metadata.
  - Added fake-provider source-aware profile flow, source-compatible indexed retrieval, clip/window storage, waveform cache DTOs, and import-safe UI workflow DTOs.
  - Added Phase 7 integration and 100-track synthetic smoke coverage with partial-failure handling.
  - Refreshed `docs/REPO_AUDIT.md` with the current Phase 7 product surface and manual QA checklist.
- **Verification:**
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`
- **Notes:**
  - Core verification remains dependency-light and does not require FAISS, PySide, Demucs, learned embeddings, cloud services, installers, or heavy MIR extras.

## 2026-05-20 — Phase 7 beta acceptance opening

- **Agent:** Codex
- **Scope:** Open Phase 7 user-facing beta acceptance hardening.
- **Rows touched:** P7-001, P7-002 → DONE.
- **Changes:**
  - Added Phase 7 FILE_PLAN rows through `scripts/update_plan.py`.
  - Promoted `ACTIVE_PHASE` from 6 to 7.
  - Documented the Phase 7 beta-acceptance boundary for explicit profiles, idempotent reruns, dependency-light source-aware acceptance, and import-safe UI/controller seams.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py`
  - `python3 scripts/status.py`

## 2026-05-20 — Phase 6 indexed library beta

- **Agent:** Codex
- **Scope:** Open Phase 6 and implement dependency-light indexed search over persisted SQLite feature views.
- **Rows touched:** P6-001 .. P6-014 → DONE.
- **Changes:**
  - Added Phase 6 plan rows, promoted `ACTIVE_PHASE` to 6, and documented the indexed-library beta boundary.
  - Added SQLite feature query APIs, a store-backed `FeatureService` path, and stable sorted stats vector reads.
  - Added `IndexService` to build one persisted FAISS/NumPy index per feature type and owner type, write manifest metadata, and detect stale or missing indexes.
  - Split similarity candidate retrieval from reranking, using current indexes when available and persisted scan fallback with explicit backend/caveat metadata.
  - Added dependency-light CLI commands for SQLite library analysis, index building, and indexed search.
  - Added resumable build-index job metadata helpers and import-safe UI DTO fields for index status and indexed result metadata.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py tests/test_phase6_cli.py tests/test_sqlite_feature_queries.py tests/test_store_feature_service.py tests/test_index_service.py tests/test_indexed_similarity.py tests/test_phase6_jobs.py tests/test_phase6_ui_models.py tests/test_phase6_integration.py tests/test_phase6_performance.py`
  - `uv run ruff check src/deep_sound/services/index_service.py src/deep_sound/services/feature_service.py src/deep_sound/services/similarity_service.py src/deep_sound/infra/storage/sqlite_store.py src/deep_sound/cli.py src/deep_sound/ui/query_builder.py src/deep_sound/ui/results_view.py tests/test_sqlite_feature_queries.py tests/test_store_feature_service.py tests/test_index_service.py tests/test_indexed_similarity.py tests/test_phase6_cli.py tests/test_phase6_jobs.py tests/test_phase6_ui_models.py tests/test_phase6_integration.py tests/test_phase6_performance.py`
  - `uv run mypy src/deep_sound`
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`
- **Notes:**
  - Core verification does not require FAISS, PySide, Demucs, learned embeddings, cloud services, or heavy MIR extras.
  - Indexes are treated as acceleration only; persisted feature rows remain canonical and stale/missing indexes fall back to scans.

## 2026-05-20 — Phase 4 correction loop and feedback-aware ranking

- **Agent:** Codex
- **Scope:** Implement bounded user correction overlays and deterministic feedback-aware reranking.
- **Rows touched:** P4-003 .. P4-012.
- **Changes:**
  - Added typed correction payloads for source labels/types, chord labels, and result feedback.
  - Added `CorrectionService` over the existing SQLite `corrections` table with effective source/chord reads.
  - Added source label/type overlays in `SourceService` without mutating raw source rows.
  - Added relevant/irrelevant result feedback and bounded optional reranking in `SimilarityService`.
  - Added explanation metadata and import-safe UI DTOs for correction controls and feedback-adjusted result cards.
- **Verification:**
  - `uv run pytest tests/test_corrections_domain.py tests/test_correction_service.py tests/test_source_corrections.py tests/test_chord_corrections.py tests/test_result_feedback.py tests/test_feedback_reranking.py tests/test_correction_explanations.py tests/test_correction_ui_models.py tests/test_sqlite_store.py tests/test_source_service.py tests/test_chord_similarity.py tests/test_explanation_service.py tests/test_source_graph_ui.py tests/test_ui_models.py`
  - `uv run ruff format --check src/deep_sound tests`
  - `uv run ruff check src/deep_sound tests`
  - `uv run mypy src/deep_sound`
- **Notes:**
  - Raw analyzer outputs and baseline records remain inspectable separately from user overrides.
  - Feedback adjustments are deterministic, capped at +/-0.10, and exposed separately from dimension scores.

## 2026-05-20 — Phase 4 control-plane opening

- **Agent:** Codex
- **Scope:** Open Phase 4 for bounded correction overrides and feedback-aware ranking.
- **Rows touched:** P4-001, P4-002.
- **Changes:**
  - Added Phase 4 FILE_PLAN rows P4-001 through P4-012 through `scripts/update_plan.py`.
  - Promoted `ACTIVE_PHASE` from 3 to 4.
  - Documented the Phase 4 boundary: corrections remain separate from raw outputs, ranking adjustments are bounded and explainable, and no model training is introduced.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py`
  - `python3 scripts/status.py`

## 2026-05-20 — Phase 3 source-specific harmonic analysis

- **Agent:** Codex
- **Scope:** Implement deterministic Phase 3 source-specific harmonic analysis without Phase 4 correction learning.
- **Rows touched:** P3-003 .. P3-012.
- **Changes:**
  - Added probabilistic pitched-harmonic source discovery for compatible broad stems.
  - Added chord/note event domain records and SQLite round-trip DAOs.
  - Added AnalysisService source routing guardrails and a conservative chroma-template source chord analyzer.
  - Added roman/root-motion normalization helpers plus source-owned chord sequence and chord-change feature views.
  - Added source chord search metadata, caveated explanations, and import-safe UI DTO enablement for compatible source modes.
- **Verification:**
  - `uv run pytest tests/test_source_service.py tests/test_source_harmonic_discovery.py tests/test_sqlite_store.py tests/test_harmonic_event_store.py tests/test_analysis_service.py tests/test_source_chord_routing.py tests/test_source_chord_analyzer.py tests/test_harmony_normalization.py tests/test_chord_feature_views.py tests/test_chord_similarity.py tests/test_stem_search.py tests/test_explanation_service.py tests/test_chord_explanations.py tests/test_ui_models.py tests/test_source_graph_ui.py tests/test_phase3_ui_models.py`
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run mypy src/deep_sound`
- **Notes:**
  - Chord labels are deterministic chroma-template estimates, not transcription truth.
  - Correction learning and user-edit workflows remain Phase 4.

## 2026-05-20 — Phase 3 control-plane opening

- **Agent:** Codex
- **Scope:** Open Phase 3 for source-specific harmonic analysis.
- **Rows touched:** P3-001, P3-002.
- **Changes:**
  - Added Phase 3 FILE_PLAN rows P3-001 through P3-012 through `scripts/update_plan.py`.
  - Promoted `ACTIVE_PHASE` from 2 to 3.
  - Documented the Phase 3 boundary: probabilistic source/chord output only, routed chord analysis only for compatible sources, and no Phase 4 correction learning.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py`
  - `python3 scripts/status.py`

## 2026-05-20 — Phase 2 broad stem analysis

- **Agent:** Codex
- **Scope:** Promote Phase 2 and implement dependency-light broad stem analysis plus Phase 3-safe UI/search hooks.
- **Rows touched:** P2-001 .. P2-012.
- **Changes:**
  - Added safe `scripts/update_plan.py --add-row` support and used it to create the Phase 2 backlog.
  - Promoted `ACTIVE_PHASE` to 2.
  - Added optional Demucs provider boundary plus deterministic fake broad-stem provider for core tests.
  - Persisted broad-stem provenance fields and added SourceService source graph APIs.
  - Added conservative drum, bass, and other-stem analyzers with confidence-bounded outputs.
  - Extended AnalysisService, stem-level search metadata, cautious explanations, and import-safe source graph UI DTOs.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py`
  - `uv run pytest tests/test_demucs_provider.py tests/test_source_service.py tests/test_analysis_service.py tests/test_drum_features.py tests/test_bass_features.py tests/test_stem_harmony.py tests/test_stem_search.py tests/test_source_graph_ui.py tests/test_explanation_service.py tests/test_sqlite_store.py`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src/deep_sound`
  - `uv run pytest`
- **Notes:**
  - A real Demucs smoke was not run because core verification does not require the heavy `[demucs]` extra.
  - Phase 3 source-specific chord analysis remains intentionally disabled/deferred.

## 2026-05-20 — Phase 1 desktop MVP backbone

- **Agent:** Codex
- **Scope:** Complete the remaining Phase 1 desktop MVP backbone.
- **Rows touched:** P1-003, P1-004, P1-005, P1-006, P1-007, P1-008, P1-009, P1-010 → DONE.
- **Changes:**
  - Added an in-memory job queue with typed jobs, progress, structured errors, cancellation, and deterministic tests.
  - Added AnalysisService orchestration for full-mix rhythm, chroma, and MFCC feature views persisted through SQLite.
  - Added a FAISS-compatible vector index with normalized vectors, JSON manifest persistence, and a NumPy fallback for core installs.
  - Added cautious explanation summaries with low-confidence caveats.
  - Added import-safe Phase 1 UI modules for the main window, track detail, query builder, and results view; PySide remains optional.
- **Verification:**
  - `uv run pytest tests/test_sqlite_store.py tests/test_library_service.py tests/test_job_queue.py tests/test_analysis_service.py tests/test_faiss_index.py tests/test_explanation_service.py tests/test_ui_models.py`
  - `uv run ruff check src/deep_sound/ui tests/test_ui_models.py`
  - `uv run mypy src/deep_sound/ui`
  - `python3 scripts/verify.py`
  - `python3 scripts/status.py`
  - `python3 scripts/toolset_review.py`

## 2026-05-20 — Phase 5 advanced similarity slice

- **Agent:** Codex
- **Scope:** Open Phase 5 and implement deterministic advanced similarity feature families.
- **Rows touched:** P5-001 .. P5-013 → DONE; P5-014 in progress for closeout.
- **Changes:**
  - Added Phase 5 plan rows and promoted `ACTIVE_PHASE` to 5 with a deterministic proxy boundary decision.
  - Added production texture and melody contour analyzers using lightweight signal descriptors with confidence-bounded outputs.
  - Added additive `AnalysisService` methods for production texture, structure sequence features, melody contour, and source timbre proxies without changing `analyze()`.
  - Added production, structure, melody, vocal timbre, source-role, and advanced search modes over normalized per-dimension scores.
  - Extended import-safe query/result DTOs and explanations with Phase 5 metadata while preserving chord-specific caveats.
- **Verification:**
  - `uv run pytest tests/test_update_plan.py`
  - `uv run pytest tests/test_similarity.py tests/test_stem_search.py tests/test_chord_similarity.py tests/test_feedback_reranking.py tests/test_explanation_service.py tests/test_ui_models.py tests/test_source_graph_ui.py tests/test_correction_ui_models.py tests/test_phase3_ui_models.py tests/test_production_texture.py tests/test_phase5_analysis_service.py tests/test_structure_features.py tests/test_melody_contour.py tests/test_phase5_similarity.py tests/test_source_role_matching.py tests/test_phase5_ui_models.py tests/test_phase5_explanations.py`
  - `python3 scripts/verify.py`
- **Notes:**
  - The first melody contour implementation used `librosa.piptrack`, but this environment segfaulted in numba during tests. It was replaced with an STFT dominant-bin contour proxy to keep core verification stable and dependency-light.

## 2026-05-20 — Phase 1 storage and library import

- **Agent:** Codex
- **Scope:** Implement Phase 1 SQLite storage and library import.
- **Rows touched:** P1-001, P1-002 → DONE.
- **Changes:**
  - Added stdlib SQLite schema and narrow DAO methods for tracks, stems, sources, source activity, feature views, similarity indices, corrections, and jobs.
  - Added Phase 1 track metadata fields and stem artifact-path metadata.
  - Added LibraryService file/folder import with `soundfile.info`, filename-title fallback, SHA-256 dedupe, failed-file job recording, and batch continuation.
  - Added storage and library tests covering schema, DAO round trips, dedupe, import failures, folder recursion, and original-audio immutability.
- **Verification:**
  - `uv run pytest tests/test_sqlite_store.py tests/test_library_service.py`
  - `uv run mypy src/deep_sound`
  - `python3 scripts/verify.py`

## 2026-05-20 — Phase 0 search completion

- **Agent:** Codex
- **Scope:** Complete the Phase 0 CLI analysis/search chain.
- **Rows touched:** P0-015, P0-016, P0-017, P0-018, P0-020, P0-021, P0-022, P0-023 → DONE.
- **Changes:**
  - Added MFCC mean/std timbre summaries with silence handling.
  - Added in-memory feature storage and weighted cosine similarity.
  - Added `search-similar` CLI over an on-demand `--corpus-dir` scan.
  - Added focused tests for MFCC, feature storage, similarity, and CLI search.
- **Verification:**
  - `uv run pytest tests/test_mfcc.py`
  - `uv run pytest tests/test_feature_service.py`
  - `uv run pytest tests/test_similarity.py`
  - `uv run pytest tests/test_search_cli.py`
  - `python3 scripts/verify.py`
- **Notes:**
  - Phase 0 remains in-memory and read-only over original audio files; SQLite, FAISS, and UI work remain Phase 1.

## 2026-05-20 — Phase 0 chroma analyzer

- **Agent:** Codex
- **Scope:** Implement Phase 0 track-level chroma feature extraction.
- **Rows touched:** P0-014, P0-019 → DONE.
- **Changes:**
  - Added a librosa-backed chroma analyzer returning a normalized 12-bin summary.
  - Added focused chroma tests covering tonal input and silence.
- **Verification:**
  - `uv run pytest tests/test_chroma.py`
  - `python3 scripts/verify.py`
- **Notes:**
  - `librosa.feature.chroma_stft` is called with `tuning=0.0` to avoid environment-dependent tuning estimation and keep Phase 0 deterministic.

---

## 2026-05-19 — Codex harness and repo audit pass

- **Agent:** Codex
- **Scope:** Repo-wide audit plus dual-surface harness work.
- **Rows touched:** none in `FILE_PLAN.md`; temporary harness-first override documented in `DECISIONS.md`.
- **Changes:**
  - Added `docs/REPO_AUDIT.md` to inventory the current repo surface.
  - Added `docs/AGENT_HARNESS_SPEC.md` to formalize the shared `.claude/` and `.codex/` control plane.
  - Added `.codex/` agents, skills, hooks, and operator docs.
  - Added `scripts/toolset_review.py` and a `make toolset-review` target for suggest-only harness recommendations.
- **Notes:**
  - The shared backend remains `scripts/status.py`, `scripts/verify.py`, `scripts/repair.py`, and `scripts/update_plan.py`.
  - Product implementation remains Phase 0 scaffold plus the existing tempo CLI path.

## 2026-05-15 — Scaffolding sprint

- **Agent:** Claude Code (plan-mode session)
- **Scope:** Initial repo scaffold; Phase 0 partial.
- **Rows touched:** P0-001 .. P0-013 → DONE.
- **Decisions:**
  - Use `uv` as the package manager (fast, single lockfile).
  - Heavy extras (`demucs`, `ui`, `index`, `mir`) deferred behind optional groups so Phase 0 install stays light.
  - Self-repair triggered by Claude Code Stop hook → `scripts/verify.py` → `.build/repair_brief.md`; capped at 3 attempts.
  - FILE_PLAN edits enforced through `scripts/update_plan.py` only; direct edits denied by settings.
  - Test fixture is a 120-BPM **click track** (not a pure sine) so the tempo analyzer has onsets to lock to.
  - Confidence for Phase 0 tempo derived as `min(1.0, len(beats) / max(1, duration_sec * 0.5))`. Placeholder, see DECISIONS.md.
  - CI installs `--extra dev` only at scaffold time; later phases extend.
- **Commit:** see `git log` for the scaffolding commit.
