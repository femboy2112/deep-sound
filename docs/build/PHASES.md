# Build Phases

**ACTIVE_PHASE:** 9

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
