# Build Phases

**ACTIVE_PHASE:** 0

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
