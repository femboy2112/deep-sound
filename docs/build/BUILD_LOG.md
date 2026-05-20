# Build Log

Append-only journal of build sessions. Newest entries at the top.

---

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
