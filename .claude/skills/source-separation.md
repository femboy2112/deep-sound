---
name: source-separation
description: Patterns and constraints for source separation work. Triggers on "demucs", "stem separation", "vocals", "drums stem", "bass stem", "accompaniment", "separate stems". Use when implementing stem separation (Phase 2) or source discovery (Phase 3).
---

# Source separation patterns

Authoritative source: spec §12.4 (broad stems), §12.5 (sub-source discovery), §12.6 (source-type routing), §17.2 (artifact versioning).

## Broad-stem separation (spec §12.4)

For Phase 2 we separate each track into:

```
full_mix · vocals · drums · bass · other/accompaniment
```

Recommended tool: Demucs (`demucs>=4.0`). Behind the `[demucs]` extra — `uv sync --extra demucs` to install.

Every separated stem records (spec §11.2 `stems`, §17.2):

- `model_name`, `model_version`
- `confidence` — optional reliability estimate
- Stem audio artifact path **or** derived feature data only (per user setting, see spec §17 / §24.4)

## Sub-source discovery (spec §12.5)

The `other/accompaniment` stem hosts multiple sources. Discovery uses:

- spectral clustering
- timbre embeddings
- source activity patterns
- pitch stability
- transient density
- stereo position
- harmonic/percussive separation
- instrument tagging models
- user correction feedback

## Source-type routing (spec §12.6) — HARD RULE

The detected `source_type` decides which analyzers run.

| Source type | Allowed analyzers |
|---|---|
| `drum_source` | beat, onset, groove, drum timbre, hit density |
| `bass_source` | pitch contour, root motion, bass rhythm, bass timbre |
| `pitched_harmonic_source` | chroma, transcription, chords, voicing, harmonic rhythm, timbre |
| `melodic_source` | melody contour, range, phrase shape, vibrato, timbre |
| `texture_source` | spectral movement, density, sustain, timbre, production texture |
| `effect_source` | onset, duration, energy curve, spectral sweep |
| `unknown` | safe general features only |

Never present nonsensical analysis (e.g. a hi-hat "chord progression") in normal results.

## Confidence on every label

Source labels are probabilistic. Use:

```python
source = Source(
    ...,
    source_label="likely electric guitar / midrange harmonic source",
    confidence=Confidence(0.78),
)
```

Never assert `"This is Guitar 2 playing Am7"`. Spec §3.3.

## Privacy (spec §24.4)

Cached stem audio is sensitive. Settings must allow:
- disable stem artifact storage,
- store features only,
- delete cached stems,
- delete all analysis artifacts.
