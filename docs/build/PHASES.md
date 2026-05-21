# Build Phases

**ACTIVE_PHASE:** 15

The line above is the build ceiling. Pickers and gating scripts read it literally. Promote it via `/phase <n>` once a phase's exit criteria are met.

---

## Phase 0 — Prototype CLI

**Goal:** Prove the analysis loop without UI complexity (spec §19).

**Required capabilities:**
- Import a small test corpus.
- Extract rhythm (tempo + beats), chroma, MFCC, and a simple embedding.
- Persist feature files.
- Command-line search by `rhythm | harmony | timbre | weighted`.

**Exit criteria:**
- `uv run deep-sound analyze <wav>` prints tempo and confidence. ✅ scaffolded
- `uv run deep-sound search-similar <wav> --mode rhythm` returns ranked matches.
- `make verify` green.

**FILE_PLAN ids:** `P0-001` .. `P0-0NN`.

---

## Phase 1 — Desktop MVP

**Goal:** Usable local desktop app for whole-track and clip similarity (spec §19, §20).

**Required capabilities:**
- Library import (files + folders).
- Waveform preview, clip selection.
- Full-mix analysis pipeline.
- Rhythm / harmony / timbre vector search.
- Weighted search sliders.
- Result cards with score breakdowns.

**Exit criteria (spec §20):**
- ≥100 tracks importable without freezing the UI.
- Search by rhythm, harmony, timbre, and weighted combinations all functional.
- Failed files reported per-track, batch continues.
- Original audio untouched.

**FILE_PLAN ids:** `P1-001` .. `P1-0NN`.

---

## Phase 2 — Broad Stem Analysis

**Goal:** Source-aware retrieval at broad-stem level.

**Required capabilities:**
- Vocals / drums / bass / other separation (Demucs).
- Drum similarity.
- Bassline / root-motion similarity.
- Accompaniment harmony analysis.
- Stem-level timbre analysis.
- Source graph view.

**FILE_PLAN ids:** `P2-001` .. `P2-0NN`.

---

## Phase 3 — Source-Specific Harmonic Analysis

**Goal:** Instrument-specific chord progression matching.

**Required capabilities:**
- Detect likely pitched harmonic sources with confidence.
- Per-source chord analysis (chord/roman/inversion/voicing).
- Search by source chord progression.
- Search by chord-change timing.
- Surface confidence and caveats in results.

**FILE_PLAN ids:** `P3-001` .. `P3-0NN`.

---

## Phase 4 — Correction Loop and Learning

**Goal:** Improve quality through user feedback.

**Required capabilities:**
- Source label correction.
- Chord correction.
- Relevant / irrelevant match feedback.
- Correction-aware re-ranking.

**FILE_PLAN ids:** `P4-001` .. `P4-0NN`.

---

## Phase 5 — Advanced Similarity and Production Features

**Goal:** Deeper phenomenological matching.

**Potential capabilities:**
- Production texture similarity.
- Arrangement graph comparison.
- Melody contour matching.
- Vocal timbre matching.
- Structural similarity.
- Cross-song source role matching.

**FILE_PLAN ids:** `P5-001` .. `P5-0NN`.

---

## Phase 6 — Indexed Library Beta

**Goal:** Make persisted libraries searchable end to end with dependency-light indexed retrieval.

**Required capabilities:**
- Query persisted SQLite feature views by owner/type and stable numeric vector.
- Build one optional acceleration index per feature type and owner type using the existing FAISS/NumPy wrapper.
- Detect missing or stale indexes and fall back to trusted persisted scans with explicit metadata.
- Keep candidate retrieval and reranking separate, including Phase 4 feedback adjustment metadata.
- Expose import/analyze/index/search flows through CLI/service/UI DTO seams without requiring FAISS, PySide, Demucs, or MIR extras.

**FILE_PLAN ids:** `P6-001` .. `P6-0NN`.

---

## Phase 7 — User-Facing Beta Acceptance Hardening

**Goal:** Turn indexed search into a coherent real-library workflow for beta acceptance.

**Required capabilities:**
- Analyze imported libraries through explicit `minimal`, `searchable`, and `source_aware` profiles.
- Re-run analysis and indexing idempotently without duplicate feature failures.
- Build profile-matched indexes while keeping persisted feature rows canonical.
- Search with hydrated track/source metadata, backend disclosure, caveats, and per-dimension scores.
- Add clip/window, waveform/cache, and import-safe UI controller seams without requiring PySide at import time.
- Keep fake-provider source-aware acceptance paths dependency-light; Demucs, FAISS, PySide, learned embeddings, cloud services, and heavy MIR extras remain optional.

**FILE_PLAN ids:** `P7-001` .. `P7-0NN`.

---

## Phase 8 — Desktop Beta Workflow Integration

**Goal:** Turn the import-safe service and DTO seams into a usable desktop beta workflow for local QA without making PySide a default verification dependency.

**Required capabilities:**
- Persist app settings for library database path, app data directory, active analysis profile, and last query.
- Route desktop intents for import, profile analysis, profile indexing, search, waveform cache generation, clip selection, and feedback through existing services.
- Map long-running analyze, index, and waveform work to visible job/progress DTOs and failure records.
- Render query, waveform/clip, hydrated result, stale-index, source-detail, and feedback DTOs without requiring PySide imports.
- Keep source, chord, event, and result language confidence/caveat based.

**FILE_PLAN ids:** `P8-001` .. `P8-0NN`.

---

## Phase 9 — Interactive Desktop Beta Hardening

**Goal:** Move from import-safe desktop workflow seams to real interactive PySide desktop wiring with background execution, clip-owned search, and manual QA hardening.

**Required capabilities:**
- Bootstrap a PySide app/window around an injected `DesktopWorkflowController`.
- Connect main-window actions, selection changes, query builder controls, result feedback actions, waveform/clip selection, and source graph/detail controls to controller intents.
- Keep analysis, indexing, waveform cache generation, and clip feature materialization off the UI thread through a Qt-compatible runner adapter.
- Materialize clip-owned feature views before clip search using existing analyzers and storage policy.
- Preserve visible backend, stale-index, caveat, confidence, and correction metadata in all interactive result/source views.
- Keep PySide smoke tests optional and skipped unless `[ui]` is installed.

**FILE_PLAN ids:** `P9-001` .. `P9-0NN`.

---

## Phase 10 — Optional Real Source-Aware Smoke

**Goal:** Prove the source-aware pipeline can run against real Demucs-separated stems when optional dependencies are installed, without changing the dependency-light default gate.

**Required capabilities:**
- Keep `source_aware` on the deterministic fake-provider path for core tests and default CLI/controller usage.
- Add explicit `source_aware_real` analysis routing backed by `DemucsProvider`.
- Fail with a clear opt-in error when `source_aware_real` is selected without a Demucs executable.
- Persist real stem artifacts under `app_data/`, preserve original audio bytes, and retain algorithm/model/params/input provenance on stem rows.
- Keep optional real-Demucs smoke coverage skipped unless the Demucs executable and a local fixture are provided intentionally.

**Exit criteria:**
- `python3 scripts/verify.py` remains green without Demucs, PySide, FAISS, learned embeddings, cloud services, or heavy MIR extras.
- Focused Phase 10 tests cover missing-Demucs errors, fake-provider compatibility, real-provider routing through a fake executable, artifact placement, and optional smoke skip behavior.

**FILE_PLAN ids:** `P10-001` .. `P10-0NN`.

---

## Phase 11 — Live Beta QA Hardening

**Goal:** Make real-user beta validation repeatable before packaging or deeper MIR quality work.

**Required capabilities:**
- Run a repo-local live QA harness against a small real-audio corpus or generated fixture set.
- Capture import, analysis, indexing, search, waveform, clip, feedback, source-aware real smoke, and optional PySide smoke evidence in `.build/live_qa_report.{json,md}`.
- Keep default verification dependency-light; Demucs, PySide, FAISS, learned models, cloud services, and audio devices remain explicit opt-in live gates.
- Surface live gate failures as actionable evidence, with skipped optional gates distinguished from passes and failures.
- Preserve source, chord, event, result, and playback inspection language as confidence-aware and caveated.
- Keep original audio read-only and all generated app artifacts under the configured app data directory.

**Exit criteria:**
- `python3 scripts/verify.py` remains green without optional heavy extras.
- `python3 scripts/live_qa.py --fixture-mode generated` writes a live QA report with passed required gates and explicit optional-skip entries.
- Manual QA docs, repo audit, decisions, and build log describe the live beta evidence standard and known-failure logging expectations.

**FILE_PLAN ids:** `P11-001` .. `P11-0NN`.

---

## Phase 12 — CPU-Only Real Smoke Stabilization

**Goal:** Make real PySide and real Demucs smoke testing routine when local optional dependencies are available, without changing the dependency-light default verification gate.

**Required capabilities:**
- Resolve the `[demucs]` extra against CPU-only PyTorch and Torchaudio wheels by default.
- Keep GPU/CUDA Demucs support out of scope for this phase and document it as future work.
- Run PySide smoke automatically when PySide is installed, with offscreen Qt for local harness usage.
- Run real Demucs smoke automatically when Demucs and its dependencies are installed, using a generated fixture when no local fixture is supplied.
- Preserve required gate failures in `.build/live_qa_report.{json,md}`; missing dependencies are skips only under `auto` policy.
- Keep `python3 scripts/verify.py` dependency-light and free of required PySide, Demucs, CUDA, FAISS, learned-model, cloud-service, or audio-device dependencies.

**Exit criteria:**
- `uv sync --extra ui --extra demucs` resolves without CUDA/NVIDIA/Triton packages in the default CPU Demucs path.
- `python3 scripts/live_qa.py --fixture-mode generated --real-smoke-policy auto` records real smoke passes when local dependencies are present and skips only when they are absent.
- `python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke --run-demucs-smoke --real-smoke-policy required` fails on missing optional dependencies instead of rewriting missing gates as skips.
- Phase closeout records full verify plus real PySide and real Demucs smoke evidence when the local environment supports them.

**FILE_PLAN ids:** `P12-001` .. `P12-0NN`.

---

## Phase 13 — Real Playback Transport Beta

**Goal:** Replace placeholder playback inspection with a guarded local playback path for imported tracks, while preserving dependency-light default verification.

**Required capabilities:**
- Keep playback output disabled by default; real device output is available only with the `[playback]` extra and explicit opt-in.
- Route play, pause, stop, and seek through import-safe service/controller seams that expose inspectable `PlaybackState`.
- Clamp seek positions, stop local device output safely, and surface decode/device failures as failed playback state instead of uncaught UI errors.
- Wire track-detail and main-window playback controls without requiring PySide at import time.
- Add live QA playback smoke policy with `auto|required|off`, generated audio, immediate stop, and original-audio immutability.

**Exit criteria:**
- `python3 scripts/verify.py` remains green without audio device access.
- `python3 scripts/live_qa.py --fixture-mode generated --playback-smoke-policy auto` records playback smoke as pass or skipped optional evidence.
- `DEEP_SOUND_RUN_PLAYBACK_SMOKE=1 uv run pytest tests/test_phase13_live_playback_smoke.py -vv` is available as an explicit real-device smoke.

**FILE_PLAN ids:** `P13-001` .. `P13-0NN`.

---

## Phase 14 — MIR Quality Baseline And Deterministic Analyzer Upgrade

**Goal:** Improve measurable MIR quality for deterministic chord, melody, bass,
drum, source-timbre, and explanation paths without changing the dependency-light
default verification gate.

**Required capabilities:**
- Add a generated-fixture MIR quality harness that writes
  `.build/mir_quality_report.json` and `.build/mir_quality_report.md`.
- Add an explicit `quality` analysis profile that reuses current storage,
  fake-provider source routing, and deterministic analyzers.
- Replace fixed-only source chord segmentation with chroma-change-aware segments
  and confidence-bounded calibration.
- Improve melody contour proxies with smoothing, voicing/activity metrics, and
  explicit low-confidence behavior.
- Add richer normalized bass, drum, and source-timbre stats while preserving
  feature shape compatibility and deterministic output.
- Preserve retrieval versus reranking separation, source-type compatibility
  filters, stale-index caveats, and probabilistic explanation language.

**Exit criteria:**
- `python3 scripts/mir_quality_eval.py --fixture-mode generated --strict` records
  passing generated quality gates without Demucs, PySide, FAISS, playback,
  learned models, GPU, or cloud services.
- `python3 scripts/verify.py` remains green under the default dependency-light
  environment.
- Phase closeout records status, quality harness, and toolset-review evidence.

**FILE_PLAN ids:** `P14-001` .. `P14-0NN`.

---

## Phase 15 — Beta Testing And Usability Campaign

**Goal:** Make the current beta testable as a coherent product workflow with a
repeatable campaign runner, stronger report contracts, quality-profile indexing,
desktop usability evidence, and low-risk interaction polish.

**Required capabilities:**
- Run one campaign command that records required evidence from verify, generated
  live QA, strict generated MIR quality, strict repo dive, and suggest-only
  toolset review.
- Standardize generated evidence metadata for schema version, command,
  environment, dependency policy, inputs, artifacts, required gates, optional
  gates, known skips, and follow-up items.
- Index the dependency-light `quality` profile and search quality-analyzed
  libraries through CLI and desktop controller flows while preserving stale-index
  caveats, scan fallback, and retrieval/rerank separation.
- Add an operator usability report format covering task id, action, expected
  result, observed result, status, dependency mode, evidence paths, and follow-up
  recommendations.
- Improve desktop usability states where tests expose friction: action gating
  when nothing is selected, inspectable empty/error states, deterministic widget
  object names, and clearer index/search/playback labels.

**Exit criteria:**
- `python3 scripts/verify.py` remains green without PySide, Demucs, playback
  device, FAISS, GPU packages, learned models, cloud services, or `[mir]`.
- `python3 scripts/beta_campaign.py --fixture-mode generated --real-smoke-policy off --playback-smoke-policy off`
  writes `.build/beta_campaign_report.json` and `.build/beta_campaign_report.md`
  with clear required, optional, skipped, failed, and follow-up evidence.
- `quality` profile can be analyzed, indexed, and searched through CLI and
  desktop controller flows.
- UI usability states are inspectable and test-covered for empty, failed, stale,
  invalid, and no-selection cases.
- Optional-host outcomes are recorded under the selected policy; default Phase 15
  closeout does not require fixing every optional-host failure.

**FILE_PLAN ids:** `P15-001` .. `P15-0NN`.
