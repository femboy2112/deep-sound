# Build Log

Append-only journal of build sessions. Newest entries at the top.

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
