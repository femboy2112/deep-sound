---
name: audio-pipeline
description: Use when editing analyzers, decode logic, analysis orchestration, rhythm extraction, windows, or librosa-based audio processing in Deep-Sound.
---

# Audio Pipeline

Use this skill for work under `src/deep_sound/infra/analyzers/`, `src/deep_sound/infra/audio_decoder.py`, and `src/deep_sound/services/analysis_service.py`.

## Core rules

- Original audio is never modified.
- Analysis operates on configured analysis copies only.
- Windows and feature shapes must stay consistent with `docs/PIPELINE.md` and `docs/SPEC.md`.
- Long-running work belongs off the UI thread.
- Analyzer outputs that infer labels or events must carry confidence.

## Read next when needed

- `docs/PIPELINE.md`
- `docs/ARCHITECTURE.md`
- `docs/SPEC.md`

