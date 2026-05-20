# Build Log

Append-only journal of build sessions. Newest entries at the top.

---

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

---

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
