# Pipeline — distilled

Source: [`SPEC.md` §12, §13](SPEC.md).

## Overall pipeline

```
Input audio
  → decode + normalize analysis copy (original untouched)
  → generate waveform preview
  → segment into windows
  → estimate tempo and beats
  → compute full-mix features
  → optional structural segmentation
  → optional broad source separation (vocals/drums/bass/other)
  → analyze stems
  → discover sub-sources within stems
  → classify source types
  → run source-specific analyzers
  → store feature views and events
  → update similarity indices
```

## Source type routing (spec §12.6)

The detected `source_type` decides which analyzers are allowed.

| Source type | Allowed analyzers |
|---|---|
| `drum_source` | beat, onset, groove, drum timbre, hit density |
| `bass_source` | pitch contour, root motion, bass rhythm, bass timbre |
| `pitched_harmonic_source` | chroma, transcription, chords, voicing, harmonic rhythm, timbre |
| `melodic_source` | melody contour, range, phrase shape, vibrato proxy, timbre |
| `texture_source` | spectral movement, density, sustain, timbre, production texture |
| `effect_source` | onset, duration, energy curve, spectral sweep |
| `unknown` | safe general features only |

Hard rule: the system MUST NOT present nonsensical analysis (e.g. a hi-hat "chord progression"). Routing is enforced by the Analysis Service.

## Feature categories (spec §13.1)

- **Rhythm:** tempo, beats, onset envelope, tempogram, bar-position histograms.
- **Drum:** kick/snare/hi-hat patterns, transient sharpness, groove template.
- **Harmony:** CQT/chroma, key, chord sequence, roman numerals, root movement, harmonic rhythm.
- **Source-specific chord:** chord events tied to a `source_id` with voicing, articulation, inversion estimates.
- **Bass:** pitch contour, root sequence, scale degree, interval sequence, syncopation.
- **Timbre:** MFCC stats, spectral descriptors, learned embedding.
- **Production:** loudness profile, stereo width, density, reverb proxy, transient density.
- **Global embedding:** broad semantic audio similarity vector.

## Comparison methods

- Rhythm: cosine on fixed embeddings; DTW on beat-synchronous sequences.
- Harmony: edit distance / alignment over roman numeral tokens; transposition-invariant.
- Bass: contour alignment + root-interval comparison.
- Timbre: cosine or learned metric on embeddings.
- Structure: section-sequence alignment.
