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

## 2026-05-20 — Phase 4 correction boundary

Phase 4 stores user corrections as reversible overrides and feedback records. Raw analyzer output, source records, chord events, feature views, and baseline similarity scores remain inspectable without mutation.

Correction-aware ranking is deterministic and bounded: relevant feedback may add a small transparent boost, irrelevant feedback may add a small transparent penalty, and final scores stay normalized to `[0, 1]`. Phase 4 does not train models, rewrite embeddings, or present user-edited labels as analyzer truth.

## 2026-05-20 — Phase 5 deterministic advanced similarity boundary

Phase 5 starts with deterministic, lightweight proxy features for production texture, structure, melody contour, vocal/source timbre, and source-role matching. Learned embeddings, heavy extras, and model-backed separation or melody systems remain optional follow-up work unless a later row explicitly requires them.

Advanced dimensions remain separate, normalized similarity evidence. Phase 5 must not collapse results into one opaque embedding, bypass source routing, mutate raw analyzer output, or present production, melody, structure, source-role, chord, or vocal labels as definitive.

## 2026-05-20 — Phase 6 indexed library beta boundary

Phase 6 promotes real-library search over persisted SQLite feature views. Indexes are an acceleration layer, not the source of truth: feature rows remain canonical, missing or stale indexes fall back to persisted scans, and result metadata must disclose the backend used.

The beta remains dependency-light. Core verification may use the existing NumPy fallback in the FAISS wrapper and must not require FAISS, PySide, Demucs, learned embeddings, cloud services, packaging installers, or heavy MIR extras.

## 2026-05-20 — Phase 7 user-facing beta acceptance boundary

Phase 7 hardens the existing indexed-search backend into a repeatable library workflow. Analysis profiles are explicit: `minimal` keeps the full-mix Phase 0 feature set, `searchable` adds production and structure feature families, and `source_aware` adds a core-light fake-provider source path for acceptance tests without requiring Demucs.

Analysis and indexing must be idempotent. Feature views stay canonical in SQLite, reruns replace or skip equivalent rows instead of creating duplicates, failed files are recorded per track or job, and missing or stale indexes disclose caveats while falling back to trusted scans.

The user-facing beta remains dependency-light. CLI and import-safe UI controller seams may expose import, analyze, index, search, progress, stale-index warnings, clip/window, waveform/cache, and feedback DTOs, but default verification must not require FAISS, PySide, Demucs, learned embeddings, cloud services, installers, or heavy MIR extras.

## 2026-05-20 — Phase 8 desktop beta workflow boundary

Phase 8 promotes the Phase 7 CLI/service beta into an import-safe desktop workflow seam. The desktop controller may route import, profile analysis, profile indexing, search, waveform cache generation, clip selection, source detail inspection, and result feedback through existing services.

Default verification remains dependency-light. PySide imports stay inside widget factories, and optional PySide smoke tests must skip when `[ui]` is not installed. Phase 8 does not add packaging, installers, cloud services, production Demucs quality work, or learned embeddings.

Result and source UI language remains probabilistic. Similarity dimension scores are similarity evidence, not analyzer confidence, and stale/missing-index caveats must stay visible in result inspection.

## 2026-05-20 — Phase 10 real-source smoke boundary

Phase 10 adds an explicit real-source smoke path without changing the default source-aware profile. `source_aware` remains the dependency-light fake-provider route used by default verification. `source_aware_real` is the only profile that constructs a `DemucsProvider`.

Missing Demucs is treated as a clear opt-in failure for `source_aware_real`, not as a reason for default `python3 scripts/verify.py` to fail. Optional real-Demucs smoke tests skip unless a Demucs executable and local audio fixture are intentionally provided.

Real separated stems must be copied under app data, original audio files must remain unchanged, and stem records must persist algorithm, model, params hash, and input hash provenance before downstream stem/source analyzers run.

## 2026-05-20 — Phase 11 live beta QA boundary

Phase 11 promotes live beta validation as a repeatable evidence loop, not as a new default dependency set. The required gate remains `python3 scripts/verify.py`; live corpus, real Demucs, PySide, audio-device playback, FAISS, learned models, and cloud-backed services stay opt-in.

The live QA harness must write `.build/live_qa_report.json` and `.build/live_qa_report.md` with pass, fail, and skipped-optional states separated. A missing optional dependency is evidence to record, not a hidden success. A requested live gate that runs and fails must remain a failure with enough command and artifact context to reproduce.

Playback work in this phase is limited to import-safe inspection seams and UI/controller action DTOs. It must not require PySide or a local audio output device during default tests, and it must never mutate original audio files.

`python3 scripts/live_qa.py --fixture-mode generated` is the dependency-light live evidence command. It may create generated fixtures, a temporary library database, indexes, waveform caches, clip artifacts, and report files under `.build/`, but it must hash-check the generated original fixtures and keep workflow artifacts under the configured app data directory. PySide and real-Demucs live gates are opt-in flags and remain visible as separate optional outcomes.

## 2026-05-20 — Phase 12 CPU-only real smoke boundary

Phase 12 makes installed real-smoke gates routine without changing the default dependency-light verify contract. `python3 scripts/verify.py` remains free of required PySide, Demucs, FAISS, learned-model, cloud-service, audio-device, or GPU dependencies.

The `[demucs]` extra is CPU-only by default. `torch` and `torchaudio` resolve through uv's explicit `pytorch-cpu` index, and `torchcodec` remains on normal package resolution unless testing proves CPU index pinning is needed. Lockfile results that include `nvidia-*`, CUDA helper packages, or `triton` are treated as a Phase 12 regression.

`scripts/live_qa.py --real-smoke-policy auto` runs PySide smoke when PySide is installed and real Demucs smoke when the Demucs executable is installed. `--real-smoke-policy required` converts missing PySide or Demucs into failed gates, and `off` records real-smoke skips even if flags are supplied. Demucs smoke may use a generated fixture; no `/tmp/deep_sound_live_smoke.wav` fixture is required.

GPU/CUDA Demucs support, broader corpus QA, and separation-quality evaluation remain future work.

## 2026-05-20 — Phase 13 real playback transport boundary

Phase 13 promotes playback from inspection-only DTOs to a guarded beta transport. `PlaybackService` remains the dependency-light default; `LocalPlaybackAdapter(audio_output_enabled=True)` is the only path that may open a local audio device, and it requires the optional `[playback]` extra.

The `[playback]` extra adds `sounddevice` only. It must not be folded into default, `[ui]`, `[demucs]`, or required verification dependencies. Missing `sounddevice` or an output-capable device is skipped evidence under `--playback-smoke-policy auto` and a failure only under `required`.

Playback smoke uses generated audio, starts nonblocking playback, stops immediately, and hash-checks the generated fixture. Original imported audio files remain read-only, and device/decode errors are surfaced as `PlaybackState(status=FAILED, error_message=...)` rather than UI exceptions.
