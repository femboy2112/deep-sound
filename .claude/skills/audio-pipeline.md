---
name: audio-pipeline
description: Patterns and constraints for the audio analysis pipeline. Triggers on "decode", "audio decode", "sample rate", "window", "tempo", "beat", "onset", "analysis window", "tempogram", "librosa". Use when implementing anything under src/deep_sound/infra/analyzers, audio_decoder, or services/analysis_service.
---

# Audio pipeline patterns

Authoritative source: spec §12 (pipeline) and §13.2/13.3 (rhythm features).

## Decode policy (spec §12.2)

- Original file **never modified**.
- Resample to a configured analysis sample rate (default 22050 Hz; mono).
- Loudness normalization only for **analysis copies**, not for playback.
- Persist enough metadata to reproduce: source path, sample rate, normalization params, decoder version.

## Analysis windows (spec §12.3)

Multiple temporal granularities are indexed:

| Window | Purpose |
|---|---|
| Whole track | Overall similarity |
| Fixed 5 s | Local timbre / texture |
| Fixed 10 s | Clip search / phrase matching |
| Beat-aligned 4-bar | Rhythm / chord progression |
| Section window | Verse/chorus comparison |
| User clip | Direct query |

## Rhythm features (spec §13.2)

Required outputs from a rhythm analyzer: tempo, beats, beat confidence (when available), onset envelope, onset peaks, tempogram, beat-synchronous onset vectors, bar-position histograms.

Comparison: cosine on fixed embeddings, DTW on beat-synchronous sequences, periodicity comparison for groove feel, optional tempo-normalized matching.

## librosa idioms

```python
import librosa

y, sr = librosa.load(path, sr=22050, mono=True)
tempo, beats_frames = librosa.beat.beat_track(y=y, sr=sr)
beats_sec = librosa.frames_to_time(beats_frames, sr=sr)
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
chroma = librosa.feature.chroma_cqt(y=y, sr=sr)  # 12 x T
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)  # 13 x T
```

## Confidence (spec §3.3)

`librosa.beat.beat_track` returns no native confidence. Until a better estimator lands, the Phase 0 heuristic is `min(1.0, len(beats) / max(1, duration_sec * 0.5))`. Document any replacement in `docs/build/DECISIONS.md`.

## Pitfalls

- A pure sine wave gives `tempo=0`. Test fixtures must contain transients.
- `librosa.beat.beat_track` often half/double-counts; ranged assertions are safer than exact equality.
- Don't import torch / demucs in `infra/analyzers` — those are Phase 2.
