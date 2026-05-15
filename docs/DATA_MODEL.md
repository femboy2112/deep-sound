# Data Model — distilled

Source: [`SPEC.md` §11](SPEC.md).

## Conceptual hierarchy

```
Track
├── Sections (intro, verse, chorus, bridge, outro — each with confidence)
├── Analysis Windows (fixed 5s/10s, beat-aligned 4-bar, user clips)
├── Stems (vocals, drums, bass, other)
├── Sources (detected within stems: likely guitar, likely synth pad, ...)
│     each has source_type, source_label, confidence, parent_stem, activity ranges
├── Feature Views (rhythm, harmony, chord_sequence, bassline, melody,
│                  timbre, production, global_embedding)
└── Events (beats, onsets, notes, chords, section boundaries, source activity)
```

## SQLite tables (spec §11.2)

`tracks`, `sections`, `stems`, `sources`, `source_activity`, `feature_views`, `chord_events`, `note_events`, `similarity_indices`, `corrections`, `jobs`.

Each row records `algorithm`, `algorithm_version`, `params_hash`, `model_version`, and a `confidence` where applicable. This lets the system detect stale artifacts when algorithms change (spec §17.2, NFR-005).

## Confidence policy (spec §3.3, §23)

Every inferred label or event carries `confidence ∈ [0, 1]`. UI confidence bands:

| Range | Band |
|---|---|
| 0.80 – 1.00 | High |
| 0.60 – 0.79 | Medium |
| 0.40 – 0.59 | Low |
| < 0.40 | Very uncertain (hidden by default) |

## Feature view kinds and owners

Feature views belong to one of: `track`, `section`, `stem`, `source`, `clip`. Their `feature_type` is one of `rhythm.*`, `harmony.*`, `timbre.*`, `bass.*`, `melody.*`, `production.*`, `embedding.*` (full list spec §13.1).
