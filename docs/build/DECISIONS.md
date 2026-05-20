# Decisions (ADR-lite)

Short, dated entries for choices that aren't obvious from the spec. Most build rows do NOT need an entry here; only deviations, cross-cutting tradeoffs, or scope decisions.

Format: `## YYYY-MM-DD — Title` then short rationale.

---

## 2026-05-15 — Confidence heuristic for Phase 0 tempo

The spec (§3.3) requires every inferred label to carry a confidence in `[0, 1]`. `librosa.beat.beat_track` returns a tempo and a beat-frame array but no native confidence. For Phase 0 we use:

```
confidence = min(1.0, len(beats) / max(1, duration_sec * 0.5))
```

This rewards tracks where the beat tracker found ≥ 0.5 beats per second (typical music). It's a placeholder; replace with a model-based estimator (or `librosa.beat.plp` salience) when we tackle Phase 1's better rhythm features.

## 2026-05-15 — Click track fixture instead of pure sine

A pure sine wave has no transients, so `librosa.beat.beat_track` returns `tempo=0`. Tests use a generated click track (short impulses at 0.5 s intervals = 120 BPM) so the analyzer actually has something to lock onto. This avoids a fragile "tempo > 0" assertion against silence.

## 2026-05-15 — uv over pip+venv / poetry

`uv` is faster, handles venv + lockfile + Python install in one tool, and has good Linux Mint support. Single source of truth: `pyproject.toml` + `uv.lock`.

## 2026-05-15 — FAISS deferred from Phase 0 to Phase 1

Phase 0's similarity-search exit criterion is "ranked results by mode". A plain numpy cosine implementation is enough — no vector index required for a few hundred test tracks. FAISS arrives in `P1-005` when the library can grow beyond what's tractable for naive search.

## 2026-05-15 — Demucs / Torch behind `[demucs]` extra

Torch + Demucs is ≈2 GB. Not needed until Phase 2 (stem separation). Putting it behind an extra keeps Phase 0/1 CI builds under a minute.

## 2026-05-19 — Temporary harness-first priority override

The normal picker would move from `P0-013` to `P0-014`. For this pass, repo-control-plane work takes temporary priority so Codex gets a first-class local harness comparable to the existing `.claude/` surface.

This override is limited to:

- repo audit docs,
- harness-spec docs,
- `.codex/` agents, skills, and hooks,
- suggest-only self-review tooling under `scripts/`.

The override does not relax product-spec rules, phase ceilings, or the `FILE_PLAN.md` mutation policy. Once the harness pass is complete, normal FILE_PLAN execution resumes.

## 2026-05-19 — Suggest-only toolset review

The new `scripts/toolset_review.py` surface is intentionally non-mutating. It may inspect repo state, verify output, and repair-attempt signals, then write recommendations to `.build/toolset_review.{json,md}`.

It must not auto-edit `.codex/`, `.claude/`, `docs/`, or source files. A human or later agent decides whether to apply any recommendation.

## 2026-05-20 — Phase 2 dependency-light stem path

Phase 2 keeps Demucs optional behind the `[demucs]` extra. Core verification uses a deterministic fake broad-stem provider that writes vocals, drums, bass, and other artifacts under app data while preserving original audio bytes.

The Phase 2 analyzers intentionally emit broad-stem proxy features only. Drum output is rhythm/timbre evidence, bass output is root-motion evidence, and other/accompaniment output is chroma/timbre evidence. Source-specific chord claims, instrument-specific harmony, and correction learning remain Phase 3+ work.

## 2026-05-20 — Phase 3 harmonic source boundary

Phase 3 promotes source-specific harmonic analysis, but every source label, chord label, roman numeral, and note event remains probabilistic and confidence-bounded. Chord analyzers are routed only to compatible pitched-harmonic sources; drums, effects, texture, and unknown sources are rejected by default.

Correction learning, user-edited chord truth, and ranking updates from feedback remain Phase 4. Phase 3 may preserve compatibility with existing correction storage, but it must not train from or reinterpret corrections.
