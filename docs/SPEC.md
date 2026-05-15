
# Source-Aware Music Similarity Desktop Application Specification

**Document version:** 0.1  
**Date:** May 15, 2026  
**Intended use:** Development planning, architecture, implementation scoping, and MVP alignment  
**Baseline platform:** Desktop application  
**Recommended implementation language:** Python for MVP and V1, with a plugin boundary for future native services

---

## 1. Executive Summary

This document specifies a desktop application that analyzes recorded music, decomposes it into musically meaningful source-level representations, and searches a local known database for songs, sections, or sources that sound similar along selected dimensions.

The application is not a generic waveform matcher. It is a source-aware music information retrieval system. It should support similarity queries such as:

- Find songs with similar drums, beat, groove, or rhythmic feel.
- Find songs with the same or similar chord progression.
- Find songs with similar chord-change timing, even when the exact chords differ.
- Find songs where a specific instrument, such as guitar, piano, synth, or bass, performs a similar role.
- Find songs with similar instrumental timbre, production texture, density, or arrangement.
- Find songs whose chorus, verse, bridge, or short clip resembles a selected section of another song.

The central design principle is:

```text
Track → Section → Stem → Source → Feature Views → Similarity Indices
```

A track is not represented by a single vector. Each track is represented by many feature views at multiple levels: full mix, section, broad stem, detected source, and event sequence. This allows explainable, controllable, and source-specific retrieval.

---

## 2. Product Vision

The product should help a user answer:

> “What other songs in my known library phenomenologically resemble this song, clip, source, rhythm, harmonic movement, instrument behavior, or production texture?”

The user should be able to select a song, clip, or detected source and ask for similar items using weighted musical dimensions.

Example:

```text
Query: Chorus of Song A
Search settings:
- Guitar chord progression: 45%
- Bass root motion: 20%
- Drum groove: 20%
- Overall production timbre: 15%

Result:
1. Song B, chorus — 86% combined similarity
   Guitar harmony: 92%
   Bass motion: 88%
   Drum groove: 74%
   Production timbre: 68%
```

The product should expose why a match occurred. It should not merely say “similar.” It should say which sources, musical events, and timbral properties aligned.

---

## 3. Scope

### 3.1 In Scope

- Desktop-first application.
- Local music library import.
- Local analysis database.
- Whole-song and clip-level analysis.
- Source separation into broad stems: vocals, drums, bass, other/accompaniment.
- Secondary source discovery within broad stems where technically feasible.
- Probabilistic source labeling, such as likely guitar, likely piano, likely synth pad, likely string layer.
- Beat, onset, rhythm, and groove analysis.
- Chroma, key, chord, chord-change, and roman numeral analysis.
- Instrument-specific chord progression detection for pitched harmonic sources.
- Bass root motion and bassline analysis.
- Timbre, spectral, and production texture analysis.
- Vector search and symbolic reranking.
- User correction of source labels, chord events, and analysis mistakes.
- Explainable ranked results.

### 3.2 Out of Scope for MVP

- Cloud streaming service integration.
- Real-time live audio analysis.
- Perfect instrument separation.
- Perfect chord transcription.
- Legal acquisition of copyrighted music.
- Full digital audio workstation functionality.
- Audio remixing or stem export as a primary feature.
- Mobile application.
- Collaborative multi-user deployment.

### 3.3 Explicit Product Constraint

The system must treat source separation, chord detection, instrument detection, and transcription as probabilistic estimates. Every inferred label or event must have a confidence score where practical.

The application should never claim:

```text
This is definitely Guitar 2 playing Am7.
```

It should instead represent:

```text
Detected source: likely electric guitar / midrange harmonic source
Confidence: 0.78
Chord event: likely Am7
Confidence: 0.64
```

---

## 4. Stack Decision

### 4.1 Summary Decision

Use **Python** as the main MVP and V1 implementation language. Use a modular architecture so performance-critical or deployment-critical components can later be replaced with native services written in C++, Rust, or another language.

Recommended stack:

| Layer | Recommended Technology | Rationale |
|---|---|---|
| Desktop UI | PySide6 / Qt for Python | Native desktop UI, mature widgets, Python integration |
| Audio decoding | ffmpeg wrapper or subprocess | Broad media decoding support |
| Numerical processing | NumPy / SciPy | Standard scientific computing base |
| Music feature extraction | librosa and Essentia | Mature MIR feature extraction libraries |
| Source separation | Demucs | Broad-stem music source separation baseline |
| Audio-to-note transcription | Basic Pitch or pluggable AMT model | Useful for instrument-specific note and chord evidence |
| Local metadata store | SQLite | Embedded, local, serverless database |
| Feature blob storage | NumPy arrays, compressed arrays, or columnar files | Efficient local storage of numeric features |
| Vector search | FAISS | Efficient dense vector similarity search |
| Packaging | PyInstaller initially | Bundles application and dependencies for desktop distribution |

### 4.2 Why Python

Python is the best baseline for this application because the difficult parts are music information retrieval, machine learning inference, signal processing, and rapid experimentation. The strongest practical ecosystem for those tasks is Python.

Python also allows a single language to cover:

- desktop UI orchestration,
- batch job management,
- audio analysis pipelines,
- machine learning model inference,
- feature extraction,
- vector indexing,
- local database access,
- prototype-to-product iteration.

### 4.3 Alternatives Considered

| Language / Stack | Advantages | Disadvantages | Decision |
|---|---|---|---|
| Python + Qt | Best MIR/ML ecosystem, fast iteration, native-ish desktop UI | Packaging can be complex, performance needs process design | Selected |
| C++ + Qt | High performance, mature desktop stack | Slower development, harder ML/MIR integration | Not for MVP |
| Rust + Tauri | Strong performance, modern architecture | Weaker MIR/ML ecosystem, more glue code | Consider for V2 services |
| TypeScript + Electron | Easy UI, web-style development | Heavy desktop footprint, weaker direct MIR ecosystem | Not primary |
| C# / .NET | Good desktop tooling on Windows | Less ideal for MIR/ML ecosystem | Not primary |

### 4.4 Architecture Implication

Even though the MVP should be Python-based, the system must maintain clean service boundaries:

```text
UI Layer
Application Services
Analysis Job Engine
Feature Extractors
Model Inference Providers
Storage Layer
Similarity Search Layer
```

This allows later replacement of individual modules without rewriting the application.

---

## 5. Definitions

| Term | Definition |
|---|---|
| Track | A complete imported audio file. |
| Clip | A user-selected time range within a track. |
| Section | A musically meaningful time range, such as intro, verse, chorus, bridge, or outro. |
| Stem | A broad separated audio component such as drums, bass, vocals, or other. |
| Source | A more specific sound-producing component inferred from a stem, such as likely guitar, piano, synth pad, or snare layer. |
| Feature View | A representation of audio optimized for one comparison type, such as rhythm, harmony, timbre, or melody. |
| Event | A discrete musical occurrence, such as a beat, onset, chord, note, or section boundary. |
| Embedding | A dense numeric vector used for similarity search. |
| Symbolic Sequence | A sequence of labels or events, such as chord tokens, roman numerals, or bass root intervals. |
| Candidate Retrieval | Fast first-stage search that returns likely matches. |
| Reranking | Slower second-stage comparison applied to candidates to improve relevance. |
| Confidence | Numeric estimate of how reliable a detected label, event, or source assignment is. |

---

## 6. Core Product Goals

### 6.1 Functional Goals

| ID | Goal |
|---|---|
| G-001 | Import and index a local music library. |
| G-002 | Analyze full tracks and user-selected clips. |
| G-003 | Separate tracks into broad stems. |
| G-004 | Discover likely musical sources inside broad stems. |
| G-005 | Detect rhythm, beat, groove, and onset patterns. |
| G-006 | Detect global and source-specific harmonic patterns. |
| G-007 | Detect chord progressions in specific pitched sources. |
| G-008 | Detect bass root motion and bassline behavior. |
| G-009 | Detect timbral and production-style descriptors. |
| G-010 | Search by weighted combinations of musical similarity dimensions. |
| G-011 | Explain every search result with per-dimension scores. |
| G-012 | Allow user correction of sources, labels, and chords. |

### 6.2 Product Quality Goals

| ID | Goal |
|---|---|
| Q-001 | Analysis should be reproducible given the same application version and model versions. |
| Q-002 | Search should be fast after indexing. |
| Q-003 | Long-running analysis jobs must not freeze the UI. |
| Q-004 | The app must preserve original audio files without modification. |
| Q-005 | Inferred outputs must expose uncertainty. |
| Q-006 | The system must support partial re-analysis when algorithms or models change. |
| Q-007 | The app should work fully offline by default. |

---

## 7. Primary Users and Use Cases

### 7.1 User Types

| User Type | Needs |
|---|---|
| Music producer | Find reference tracks with similar drums, chords, arrangement, or sonic texture. |
| Composer/songwriter | Find songs with related harmonic movement or chord progressions. |
| DJ | Find songs with compatible groove, tempo, energy, and percussion style. |
| Music researcher | Inspect source-level musical behavior across a corpus. |
| Casual power user | Discover songs in a local library that sound alike in specific ways. |

### 7.2 Representative Use Cases

| ID | Use Case | Description |
|---|---|---|
| UC-001 | Find similar whole songs | User selects a track and searches for overall similar songs. |
| UC-002 | Find similar clips | User selects a 10-second section and searches for matching sections in the library. |
| UC-003 | Find similar drums | User searches using only drum groove and drum timbre. |
| UC-004 | Find same chord progression | User searches for songs with the same normalized chord progression. |
| UC-005 | Find same guitar chords | User selects a guitar-like source and searches for sources with similar chord changes. |
| UC-006 | Find same bass motion | User selects a bassline and searches for similar root motion and rhythmic placement. |
| UC-007 | Find same chord-change rhythm | User searches for songs whose chords change at similar phrase positions. |
| UC-008 | Find same timbre | User searches for similar instrumental or production timbre. |
| UC-009 | Compare arrangements | User compares which sources in two songs perform similar roles. |
| UC-010 | Correct analysis | User corrects a mistaken source label or chord and saves feedback. |

---

## 8. Functional Requirements

### 8.1 Library Import

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | User shall import individual audio files. | MVP |
| FR-002 | User shall import folders recursively. | MVP |
| FR-003 | System shall detect duplicate files using file hash and audio fingerprint where feasible. | V1 |
| FR-004 | System shall read basic metadata such as title, artist, album, duration, and filepath. | MVP |
| FR-005 | System shall preserve original files without modification. | MVP |
| FR-006 | System shall track analysis status per track. | MVP |

### 8.2 Track and Clip Selection

| ID | Requirement | Priority |
|---|---|---|
| FR-010 | User shall play imported tracks inside the app. | MVP |
| FR-011 | User shall select a time range as a query clip. | MVP |
| FR-012 | User shall view waveform overview. | MVP |
| FR-013 | User should view spectrogram and source activity overlays. | V1 |
| FR-014 | User shall search using whole track or selected clip. | MVP |

### 8.3 Source Separation and Source Discovery

| ID | Requirement | Priority |
|---|---|---|
| FR-020 | System shall separate a track into broad stems: vocals, drums, bass, other/accompaniment. | V1 |
| FR-021 | System shall store separated stem audio or derived feature data. | V1 |
| FR-022 | System should infer sub-sources within broad stems. | V1.5 |
| FR-023 | System shall assign source type, source label, and confidence to each detected source. | V1.5 |
| FR-024 | System shall allow user correction of source labels. | V1.5 |
| FR-025 | System shall track which sources are active in which sections. | V1.5 |

### 8.4 Section Detection

| ID | Requirement | Priority |
|---|---|---|
| FR-030 | System shall segment tracks into analysis windows. | MVP |
| FR-031 | System should infer larger musical sections such as intro, verse, chorus, bridge, outro. | V1 |
| FR-032 | User shall be able to rename or adjust section labels. | V1 |
| FR-033 | Section boundaries shall have confidence scores if automatically detected. | V1 |

### 8.5 Rhythm Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-040 | System shall estimate tempo. | MVP |
| FR-041 | System shall estimate beat positions. | MVP |
| FR-042 | System shall compute onset envelope and onset events. | MVP |
| FR-043 | System shall compute beat-synchronous rhythm features. | MVP |
| FR-044 | System shall compute tempogram or rhythmic periodicity features. | MVP |
| FR-045 | System shall compare drum grooves independent of absolute start time. | V1 |
| FR-046 | System should estimate swing or microtiming features. | V2 |

### 8.6 Harmony and Chord Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-050 | System shall compute chroma or pitch-class features. | MVP |
| FR-051 | System shall estimate global key where feasible. | MVP |
| FR-052 | System shall infer chord events for the full mix. | V1 |
| FR-053 | System shall normalize chord progressions to roman numerals when key confidence is sufficient. | V1 |
| FR-054 | System shall represent chord-change timing separately from chord identity. | V1 |
| FR-055 | System shall compare chord sequences transposition-invariantly. | V1 |
| FR-056 | System shall expose confidence for chord labels. | V1 |

### 8.7 Instrument-Specific Chord Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-060 | System shall identify pitched harmonic sources suitable for chord analysis. | V1.5 |
| FR-061 | System shall attempt chord analysis on likely guitar, piano, synth, string, pad, or other harmonic sources. | V1.5 |
| FR-062 | System shall avoid chord analysis on non-harmonic sources such as drums unless explicitly forced for diagnostics. | V1.5 |
| FR-063 | System shall distinguish source-specific chords from full-mix chords. | V1.5 |
| FR-064 | System shall store source-specific chord events with source ID, timing, chord label, roman numeral, inversion, and confidence. | V1.5 |
| FR-065 | System should estimate voicing spread, chord quality, extensions, and articulation where feasible. | V2 |
| FR-066 | System shall allow user correction of source-specific chord events. | V2 |

### 8.8 Bass Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-070 | System shall detect bass pitch contour where feasible. | V1 |
| FR-071 | System shall infer bass root sequence. | V1 |
| FR-072 | System shall represent bassline rhythm and syncopation. | V1 |
| FR-073 | System shall distinguish bass root evidence from full chord certainty. | V1 |
| FR-074 | System shall compare basslines by pitch contour, root movement, rhythm, and timbre. | V1 |

### 8.9 Timbre and Production Analysis

| ID | Requirement | Priority |
|---|---|---|
| FR-080 | System shall compute timbral descriptors for full mix and sources. | MVP |
| FR-081 | System shall compute spectral descriptors such as brightness, flatness, rolloff, and MFCCs. | MVP |
| FR-082 | System shall compute embeddings for broad audio similarity. | V1 |
| FR-083 | System should estimate production descriptors such as density, stereo width, dryness/reverb proxy, and spectral balance. | V2 |
| FR-084 | System shall compare timbre separately from rhythm and harmony. | MVP |

### 8.10 Similarity Search

| ID | Requirement | Priority |
|---|---|---|
| FR-090 | System shall allow search by overall similarity. | MVP |
| FR-091 | System shall allow search by rhythm similarity. | MVP |
| FR-092 | System shall allow search by harmony similarity. | MVP |
| FR-093 | System shall allow search by timbre similarity. | MVP |
| FR-094 | System shall allow weighted multi-dimensional similarity search. | MVP |
| FR-095 | System shall allow source-specific similarity search. | V1.5 |
| FR-096 | System shall return ranked results with per-dimension explanation scores. | MVP |
| FR-097 | System shall support segment-level matching, not only full-track matching. | V1 |
| FR-098 | System shall support candidate retrieval plus reranking. | V1 |

### 8.11 User Correction and Learning

| ID | Requirement | Priority |
|---|---|---|
| FR-100 | User shall be able to rename detected sources. | V1.5 |
| FR-101 | User shall be able to correct chord labels. | V2 |
| FR-102 | User shall be able to mark search results as relevant or irrelevant. | V2 |
| FR-103 | System shall store corrections separately from raw model output. | V1.5 |
| FR-104 | System should use corrections to improve future ranking or local labels. | V2 |

---

## 9. Nonfunctional Requirements

### 9.1 Performance

| ID | Requirement |
|---|---|
| NFR-001 | The UI must remain responsive during analysis jobs. |
| NFR-002 | Search over an indexed library should return initial results in under 3 seconds for typical local libraries after feature extraction is complete. |
| NFR-003 | Long-running analysis must run in background worker processes or equivalent isolated jobs. |
| NFR-004 | The system must support resumable indexing. |
| NFR-005 | The system must support per-track reanalysis when models or feature versions change. |

### 9.2 Reliability

| ID | Requirement |
|---|---|
| NFR-010 | Failed analysis of one track must not stop the whole library job. |
| NFR-011 | Every analysis artifact must record algorithm version, model version, parameters, and timestamp. |
| NFR-012 | The database must be recoverable from partial job failure. |
| NFR-013 | Feature files must be treated as cacheable artifacts that can be regenerated. |

### 9.3 Privacy and Locality

| ID | Requirement |
|---|---|
| NFR-020 | The app shall operate offline by default. |
| NFR-021 | The app shall not upload user audio unless the user explicitly enables a future cloud feature. |
| NFR-022 | The app shall store library paths and analysis artifacts locally. |
| NFR-023 | The app shall provide a clear way to delete cached stems and analysis artifacts. |

### 9.4 Explainability

| ID | Requirement |
|---|---|
| NFR-030 | Search results must include score breakdowns. |
| NFR-031 | Results must identify which section or source matched when possible. |
| NFR-032 | Results must expose uncertainty where relevant. |
| NFR-033 | The app should make it visually clear whether a result matched on rhythm, harmony, timbre, source behavior, or overall embedding. |

---

## 10. System Architecture

### 10.1 High-Level Architecture

```text
Desktop UI
  ↓
Application Controller
  ↓
Domain Services
  ├── Library Service
  ├── Playback Service
  ├── Analysis Service
  ├── Source Service
  ├── Feature Service
  ├── Similarity Service
  ├── Correction Service
  └── Reporting/Explanation Service
  ↓
Infrastructure
  ├── Audio Decoder
  ├── Model Runtime
  ├── Job Queue
  ├── SQLite Metadata Store
  ├── Feature Artifact Store
  ├── Vector Index Store
  └── Configuration Store
```

### 10.2 Major Components

| Component | Responsibility |
|---|---|
| Desktop UI | User interaction, waveform, library browser, source graph, query builder, results view. |
| Library Service | File import, metadata, duplicate tracking, analysis status. |
| Audio Decoder | Converts supported audio formats into normalized PCM analysis input. |
| Analysis Service | Orchestrates feature extraction and model inference. |
| Job Queue | Runs long tasks without freezing UI. |
| Source Service | Manages stems, detected sources, source labels, source activity, and corrections. |
| Feature Service | Stores and retrieves feature vectors, symbolic sequences, and event data. |
| Similarity Service | Handles candidate retrieval, reranking, scoring, and ranking. |
| Explanation Service | Converts score details into human-readable match explanations. |
| Storage Layer | SQLite records plus separate binary artifacts for large arrays and audio artifacts. |

### 10.3 Processing Boundary

Long-running operations must run outside the UI thread. Recommended job types:

- decode track,
- waveform preview generation,
- feature extraction,
- stem separation,
- source discovery,
- chord inference,
- index update,
- search reranking.

---

## 11. Data Model

### 11.1 Conceptual Model

```text
Track
├── Sections
├── Analysis Windows
├── Stems
│   ├── vocals
│   ├── drums
│   ├── bass
│   └── other
├── Sources
│   ├── detected source label
│   ├── source type
│   ├── parent stem
│   ├── activity ranges
│   └── confidence
├── Feature Views
│   ├── rhythm
│   ├── harmony
│   ├── chord sequence
│   ├── bassline
│   ├── melody
│   ├── timbre
│   ├── production
│   └── global embedding
└── Events
    ├── beats
    ├── onsets
    ├── notes
    ├── chords
    ├── section boundaries
    └── source activity
```

### 11.2 Required Tables

#### tracks

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Primary ID. |
| filepath | text | Original local path. |
| title | text | Track title if known. |
| artist | text | Artist if known. |
| album | text | Album if known. |
| duration_sec | real | Track duration. |
| sample_rate | int | Analysis sample rate. |
| audio_hash | text | File or audio hash. |
| import_status | text | Imported, missing, duplicate, failed. |
| created_at | datetime | Import time. |

#### sections

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Section ID. |
| track_id | string/uuid | Parent track. |
| start_sec | real | Start time. |
| end_sec | real | End time. |
| label | text | intro, verse, chorus, bridge, unknown, user-defined. |
| confidence | real | Confidence if auto-detected. |
| source | text | auto or user. |

#### stems

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Stem ID. |
| track_id | string/uuid | Parent track. |
| stem_type | text | vocals, drums, bass, other, full_mix. |
| artifact_path | text | Optional audio artifact path. |
| model_name | text | Separation model. |
| model_version | text | Model version. |
| confidence | real | Optional stem reliability estimate. |

#### sources

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Source ID. |
| track_id | string/uuid | Parent track. |
| parent_stem_id | string/uuid | Stem source came from. |
| source_type | text | drum_source, bass_source, pitched_harmonic_source, melodic_source, texture_source, effect_source, unknown. |
| source_label | text | likely guitar, likely piano, likely synth, etc. |
| confidence | real | Confidence in label. |
| user_label | text/null | User correction. |
| is_user_corrected | bool | Whether user corrected it. |

#### source_activity

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Activity record ID. |
| source_id | string/uuid | Source. |
| section_id | string/uuid/null | Optional section. |
| start_sec | real | Start time. |
| end_sec | real | End time. |
| confidence | real | Activity confidence. |

#### feature_views

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Feature view ID. |
| owner_type | text | track, section, stem, source, clip. |
| owner_id | string/uuid | Parent entity. |
| feature_type | text | rhythm, harmony, timbre, bassline, chord_sequence, global_embedding, etc. |
| vector_path | text/null | Path to numeric vector or tensor. |
| symbolic_json | text/null | Symbolic features. |
| stats_json | text/null | Summary statistics. |
| algorithm | text | Extractor name. |
| algorithm_version | text | Version. |
| params_hash | text | Parameter identity. |
| confidence | real/null | Feature confidence if applicable. |

#### chord_events

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Chord event ID. |
| owner_type | text | full_mix, stem, source. |
| owner_id | string/uuid | Entity that produced event. |
| start_sec | real | Start time. |
| end_sec | real | End time. |
| chord_label | text | C, Am7, Dsus4, etc. |
| roman_numeral | text/null | I, ii, V7, etc. |
| root | text/null | Chord root. |
| quality | text/null | major, minor, dominant, suspended, diminished, etc. |
| bass_note | text/null | Inversion or slash bass. |
| confidence | real | Chord confidence. |
| source | text | auto or user. |

#### note_events

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Note event ID. |
| owner_type | text | source, stem, full_mix. |
| owner_id | string/uuid | Entity. |
| start_sec | real | Start. |
| end_sec | real | End. |
| pitch_midi | real | MIDI pitch estimate. |
| pitch_name | text | C4, F#3, etc. |
| velocity | real/null | Optional intensity. |
| confidence | real | Note confidence. |

#### similarity_indices

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Index ID. |
| feature_type | text | Feature type indexed. |
| owner_type | text | track, section, source, etc. |
| source_type_filter | text/null | Optional source type. |
| index_path | text | FAISS or other index path. |
| manifest_path | text | Mapping from vector row to entity. |
| version | text | Index version. |
| created_at | datetime | Created time. |

#### corrections

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Correction ID. |
| entity_type | text | source, chord_event, section, result_feedback. |
| entity_id | string/uuid | Corrected entity. |
| old_value_json | text | Previous auto value. |
| new_value_json | text | User value. |
| created_at | datetime | Correction timestamp. |

#### jobs

| Field | Type | Description |
|---|---|---|
| id | string/uuid | Job ID. |
| job_type | text | analyze_track, separate_sources, build_index, etc. |
| target_type | text | track, source, library. |
| target_id | string/uuid | Entity. |
| status | text | queued, running, completed, failed, canceled. |
| progress | real | 0 to 1. |
| error_message | text/null | Failure details. |
| created_at | datetime | Time queued. |
| updated_at | datetime | Last update. |

---

## 12. Audio Analysis Pipeline

### 12.1 Pipeline Overview

```text
Input audio
→ decode and normalize analysis copy
→ generate waveform preview
→ segment into windows
→ estimate tempo and beats
→ compute full-mix features
→ optional structural segmentation
→ optional broad source separation
→ analyze stems
→ discover sub-sources
→ classify source types
→ run source-specific analyzers
→ store feature views and events
→ update similarity indices
```

### 12.2 Decode and Normalize

The system shall:

- decode input audio to an internal PCM representation,
- preserve original file unchanged,
- resample to configured analysis sample rate,
- optionally create mono and stereo analysis copies,
- normalize loudness only for analysis, not for playback or original file modification,
- store enough metadata to reproduce analysis.

### 12.3 Analysis Windows

The system should index multiple temporal granularities:

| Window Type | Use |
|---|---|
| Whole track | Overall similarity. |
| Fixed 5-second window | Local timbre and texture matching. |
| Fixed 10-second window | Clip search and local phrase matching. |
| Beat-aligned 4-bar window | Rhythm and chord progression comparison. |
| Section window | Verse/chorus/bridge comparison. |
| User-selected clip | Direct query input. |

### 12.4 Broad Stem Separation

For V1, the app should separate each track into:

```text
full_mix
vocals
drums
bass
other/accompaniment
```

These stems become analysis parents for specialized feature extraction.

### 12.5 Secondary Source Discovery

The `other/accompaniment` stem may contain several musical sources. The app should attempt secondary discovery using:

- spectral clustering,
- timbre embeddings,
- source activity patterns,
- pitch stability,
- transient density,
- stereo position,
- harmonic/percussive separation,
- instrument tagging models,
- user correction feedback.

Candidate labels should remain probabilistic:

```text
Source S03
Parent stem: other
Label: likely bright acoustic guitar
Source type: pitched_harmonic_source
Confidence: 0.72
```

### 12.6 Source Type Routing

The source type determines which analyzers are allowed.

| Source Type | Allowed Analyzers |
|---|---|
| drum_source | beat, onset, groove, drum timbre, hit density |
| bass_source | pitch contour, root motion, bass rhythm, bass timbre |
| pitched_harmonic_source | chroma, transcription, chords, voicing, harmonic rhythm, timbre |
| melodic_source | melody contour, range, phrase shape, vibrato proxy, timbre |
| texture_source | spectral movement, density, sustain, timbre, production texture |
| effect_source | onset, duration, energy curve, spectral sweep |
| unknown | safe general features only |

The system must avoid nonsensical analysis by default. For example, it should not present a hi-hat chord progression as a normal result.

---

## 13. Feature Extraction Specification

### 13.1 Feature View Categories

| Feature View | Owner Levels | Purpose |
|---|---|---|
| rhythm.global | track, section, clip | General rhythmic similarity. |
| rhythm.drum | drum stem, drum source | Groove and percussion similarity. |
| harmony.chroma | track, section, harmonic source | Tonal similarity. |
| harmony.chord_sequence | track, section, harmonic source | Chord progression matching. |
| harmony.chord_change | track, section, source | Chord-change timing and motion. |
| bass.root_motion | bass stem, bass source | Bass root sequence similarity. |
| melody.contour | vocal, lead, melodic source | Melodic shape matching. |
| timbre.mfcc_stats | track, stem, source, section | Instrumental color. |
| timbre.embedding | track, stem, source, section | Learned timbre similarity. |
| production.texture | track, section | Mix and production feel. |
| structure.section_sequence | track | Arrangement-level similarity. |
| embedding.global | track, section, clip | Broad semantic audio similarity. |

### 13.2 Rhythm Features

Required rhythm features:

- tempo estimate,
- beat positions,
- beat confidence if available,
- onset envelope,
- onset peaks,
- tempogram or periodicity descriptor,
- beat-synchronous onset vectors,
- bar-position histograms when meter is estimated.

Comparison methods:

- cosine similarity for fixed rhythm embeddings,
- dynamic time warping for beat-synchronous sequences,
- periodicity comparison for groove feel,
- optional tempo-normalized matching.

### 13.3 Drum Features

Drum-specific features should be extracted from the drum stem or detected drum sources:

- kick-like onset pattern,
- snare-like onset pattern,
- hi-hat density proxy,
- transient sharpness,
- low/mid/high drum energy distribution,
- groove template over beat subdivisions,
- drum timbre descriptors.

Drum similarity should separate:

```text
rhythmic placement
hit density
swing/microtiming approximation
drum-kit timbre
mix treatment
```

### 13.4 Harmony Features

Full-mix and harmonic-source harmony features:

- CQT or chroma representation,
- beat-synchronous chroma,
- key estimate,
- key confidence,
- chord sequence,
- roman numeral sequence,
- root movement sequence,
- chord quality sequence,
- harmonic rhythm,
- phrase-position chord changes.

The system must represent absolute and normalized forms:

```text
Absolute chords: C → G → Am → F
Roman numerals: I → V → vi → IV
Root intervals: 0 → +7 → +2 → -4
```

### 13.5 Source-Specific Chord Features

For a pitched harmonic source, the analyzer should attempt:

```text
source audio
→ beat alignment
→ chroma/CQT
→ optional note transcription
→ chord inference
→ key normalization
→ chord event sequence
→ voicing/articulation descriptors
```

Source-specific chord analysis must produce separate outputs for:

| Output | Meaning |
|---|---|
| chord_label | Absolute chord guess. |
| roman_numeral | Key-normalized harmonic function. |
| root_motion | Movement between chord roots. |
| chord_quality | Major, minor, suspended, dominant, diminished, etc. |
| extension | 7th, 9th, add9, sus4, etc. if feasible. |
| inversion | Bass note or inversion if feasible. |
| voicing_spread | Approximate pitch span of chord tones. |
| articulation | Strummed, arpeggiated, block, sustained if feasible. |
| confidence | Reliability estimate. |

### 13.6 Bass Features

Bass analysis should not overclaim full harmony. It should produce:

- pitch contour,
- note events,
- root sequence,
- scale-degree sequence when key is known,
- interval sequence,
- rhythm pattern,
- syncopation features,
- timbre descriptors,
- implied harmony evidence.

Example:

```text
Bass notes: C → G → A → F
Scale degrees: 1 → 5 → 6 → 4
Possible harmony evidence: I → V → vi → IV
Confidence: medium
```

### 13.7 Timbre Features

Timbre analysis should include:

- MFCC summary statistics,
- spectral centroid,
- spectral bandwidth,
- spectral flatness,
- spectral rolloff,
- zero-crossing rate where relevant,
- mel-spectrogram summary or embedding,
- learned audio embedding where configured,
- source-specific timbre embeddings.

### 13.8 Production Texture Features

Production similarity is different from instrument similarity. It should include approximations for:

- loudness profile,
- spectral balance,
- stereo width,
- source density,
- dynamic range,
- reverb/dryness proxy,
- transient density,
- high-frequency brightness,
- low-end weight,
- section energy curve.

---

## 14. Similarity Search Specification

### 14.1 Search Principle

The system shall use multi-view similarity. A query may use one or more weighted dimensions:

```text
combined_score = Σ(weight_i × score_i) / Σ(weight_i)
```

Each score must be normalized to a common range, preferably 0 to 1.

### 14.2 Supported Search Modes

| Mode | Uses |
|---|---|
| Overall similarity | global embedding, rhythm, harmony, timbre, structure. |
| Rhythm similarity | beat-synchronous rhythm, onset pattern, tempogram. |
| Drum similarity | drum groove, hit density, drum timbre. |
| Chord progression similarity | chord sequence, roman numeral sequence, transposition-invariant alignment. |
| Chord-change similarity | harmonic rhythm, phrase-position changes, root movement. |
| Instrument-specific chord similarity | source-level chord events, voicing, articulation, timbre. |
| Bassline similarity | root motion, contour, bass rhythm, bass timbre. |
| Timbre similarity | MFCC/spectral/embedding descriptors. |
| Production similarity | mix texture, density, loudness, spectral balance. |
| Section similarity | segment or section-level comparison. |

### 14.3 Candidate Retrieval

The first search stage should be fast approximate retrieval.

Process:

```text
1. Extract or load query feature views.
2. For each selected feature type, search its vector index.
3. Retrieve top K candidates per feature type.
4. Merge candidates by entity ID.
5. Pass merged candidate set to reranker.
```

Recommended candidate counts:

| Library Size | Top K Per Feature |
|---|---|
| < 5,000 segments | 100 |
| 5,000 to 100,000 segments | 200 to 500 |
| > 100,000 segments | 500+ with approximate index tuning |

### 14.4 Reranking

Reranking should use slower but more musically meaningful comparisons.

| Dimension | Reranking Method |
|---|---|
| Rhythm | Dynamic time warping over beat-synchronous onset vectors. |
| Chords | Edit distance or alignment over roman numeral tokens. |
| Chord changes | Alignment over timing and root-movement events. |
| Bass | Contour alignment plus root interval comparison. |
| Timbre | Cosine or learned metric over embeddings. |
| Structure | Section sequence alignment. |
| Source behavior | Source-type constrained comparison. |

### 14.5 Transposition-Invariant Harmony Matching

Songs in different keys should still match when harmonic function is equivalent.

Example:

```text
Song A: C → G → Am → F
Song B: D → A → Bm → G
Normalized: I → V → vi → IV
```

Both should receive high chord progression similarity.

### 14.6 Tempo-Invariant Rhythm Matching

The system should optionally match similar grooves at different tempos. Tempo normalization must be user-controllable because sometimes tempo itself is part of the desired similarity.

Options:

```text
[ ] Match exact tempo
[x] Allow tempo-scaled rhythm similarity
[x] Compare beat-relative groove
```

### 14.7 Source-Constrained Matching

When user selects a source-specific mode, results should compare compatible source types.

Example:

```text
Query source: likely acoustic guitar
Selected mode: instrument-specific chord progression
Preferred candidates:
- guitar-like pitched harmonic sources
- piano/synth harmonic sources if user allows cross-instrument matching
Excluded by default:
- drums
- effects
- pure texture sources without chord evidence
```

### 14.8 Explanation Output

Each result shall provide:

- combined score,
- per-dimension scores,
- matched entity type: track, section, stem, source, or clip,
- matched time range,
- confidence indicators,
- short human-readable explanation.

Example:

```text
Song B — Chorus, 1:04 to 1:36
Combined similarity: 86%

Why it matched:
- Guitar-like source uses the same normalized progression: I → V → vi → IV.
- Chord changes occur at similar bar positions.
- Bass root motion aligns closely: 1 → 5 → 6 → 4.
- Drum groove is moderately similar but uses denser hi-hats.

Scores:
Guitar chord progression: 92%
Bass root motion: 88%
Drum groove: 74%
Production timbre: 68%
```

---

## 15. User Interface Specification

### 15.1 Main Views

| View | Purpose |
|---|---|
| Library View | Import, browse, filter, analysis status. |
| Track Detail View | Waveform, playback, sections, sources, feature summaries. |
| Source Graph View | Visual tree of stems and detected sources. |
| Query Builder | Select query source, clip, and similarity weights. |
| Results View | Ranked matches with score explanations. |
| Analysis Queue View | Background job progress and failures. |
| Corrections View | User corrections and analysis overrides. |
| Settings View | Models, storage paths, performance, cache, privacy. |

### 15.2 Library View

Required elements:

- import file button,
- import folder button,
- track table,
- analysis status indicator,
- search/filter box,
- sorting by title, artist, date imported, status,
- batch analyze action,
- batch reindex action.

### 15.3 Track Detail View

Required elements:

- playback controls,
- waveform timeline,
- selectable time range,
- section markers,
- source activity lanes,
- feature summary panel,
- analyze/reanalyze controls.

### 15.4 Source Graph View

Example:

```text
Full Mix
├── Vocals
│   └── Lead vocal, confidence 0.83
├── Drums
│   ├── Kick/snare core, confidence 0.71
│   └── Hi-hat layer, confidence 0.58
├── Bass
│   └── Synth bass, confidence 0.76
└── Other
    ├── Bright guitar-like harmonic source, confidence 0.72
    ├── Sustained synth pad, confidence 0.68
    └── Noise/riser effect, confidence 0.61
```

Each node should expose:

- source label,
- source type,
- confidence,
- active time range,
- available feature views,
- user correction controls,
- search from this source action.

### 15.5 Query Builder

Required controls:

```text
Query target:
[ ] Whole track
[ ] Selected clip
[ ] Selected section
[ ] Selected stem
[ ] Selected source

Similarity dimensions:
[x] Rhythm / groove               weight 25%
[x] Chord progression             weight 25%
[x] Chord-change timing           weight 15%
[x] Instrument-specific behavior  weight 20%
[x] Timbre / production           weight 15%

Normalization:
[x] Key-invariant harmony
[x] Tempo-scaled rhythm
[ ] Require same instrument label
[x] Allow compatible source types
```

### 15.6 Results View

Each result card should include:

- track title and artist,
- matched time range,
- matched source if applicable,
- combined score,
- per-dimension scores,
- confidence warnings,
- play preview button,
- compare button,
- mark relevant/irrelevant buttons.

### 15.7 Correction UI

The user should be able to correct:

- section labels,
- source labels,
- source type,
- chord labels,
- key estimates,
- false matches,
- preferred match dimensions.

Corrections must not overwrite raw model output. They should be stored as user overrides.

---

## 16. Application Services

### 16.1 Library Service

Responsibilities:

- import files,
- read metadata,
- track file availability,
- assign track IDs,
- manage analysis status,
- expose library queries to UI.

### 16.2 Analysis Service

Responsibilities:

- schedule jobs,
- select analyzers,
- manage model execution,
- store outputs,
- update status,
- emit progress.

### 16.3 Source Service

Responsibilities:

- store stem and source records,
- manage source labels,
- manage source activity,
- apply user corrections,
- return source graph for a track.

### 16.4 Feature Service

Responsibilities:

- store feature metadata,
- read/write feature artifacts,
- validate feature versions,
- invalidate stale features,
- provide feature views to search.

### 16.5 Similarity Service

Responsibilities:

- build indices,
- query indices,
- merge candidates,
- rerank candidates,
- calculate combined score,
- return explainable result objects.

### 16.6 Explanation Service

Responsibilities:

- convert technical score details into readable explanations,
- flag low-confidence claims,
- identify matched sources and time ranges,
- generate result comparison summaries.

---

## 17. File and Artifact Storage

### 17.1 Recommended Local Folder Layout

```text
app_data/
├── database/
│   └── library.sqlite
├── features/
│   ├── rhythm/
│   ├── harmony/
│   ├── timbre/
│   ├── bass/
│   ├── melody/
│   └── embeddings/
├── indices/
│   ├── rhythm.faiss
│   ├── harmony.faiss
│   ├── timbre.faiss
│   └── manifests/
├── stems/
│   └── <track_id>/
├── waveform_cache/
├── logs/
├── models/
└── config/
    └── settings.json
```

### 17.2 Artifact Versioning

Every feature artifact must include:

- feature type,
- source entity,
- extractor name,
- extractor version,
- parameters,
- model version where applicable,
- date generated,
- input audio hash.

This is necessary so the system can detect stale analysis when algorithm versions change.

---

## 18. Analysis Job Types

| Job Type | Input | Output |
|---|---|---|
| import_track | file path | track record |
| decode_track | track | normalized analysis audio |
| build_waveform | track | waveform preview |
| analyze_full_mix | track | global rhythm, harmony, timbre features |
| segment_track | track | sections and windows |
| separate_stems | track | stems |
| analyze_stem | stem | stem-level features |
| discover_sources | stem | source records |
| analyze_source | source | source-level features and events |
| infer_chords | track/stem/source | chord events |
| transcribe_notes | source | note events |
| build_index | feature type | similarity index |
| search | query feature views | ranked results |

### 18.1 Job Behavior

All jobs shall support:

- queued/running/completed/failed/canceled states,
- progress reporting,
- structured error messages,
- retry when safe,
- versioned outputs,
- resumability for large libraries.

---

## 19. MVP Phasing

### Phase 0 — Prototype CLI

Goal: prove analysis and search without UI complexity.

Required capabilities:

- import small test corpus,
- extract rhythm, chroma, MFCC, and simple embeddings,
- create feature files,
- run command-line search by rhythm, harmony, timbre, and weighted mix.

Deliverable:

```text
analyze_track <path>
search_similar <track_or_clip> --mode rhythm|harmony|timbre|weighted
```

### Phase 1 — Desktop MVP

Goal: usable local desktop app for whole-track and clip similarity.

Required capabilities:

- library import,
- waveform preview,
- clip selection,
- full-mix analysis,
- rhythm/harmony/timbre features,
- basic vector search,
- weighted search sliders,
- score explanations.

### Phase 2 — Broad Stem Analysis

Goal: source-aware retrieval at broad-stem level.

Required capabilities:

- vocals/drums/bass/other separation,
- drum similarity,
- bass root motion similarity,
- accompaniment harmony analysis,
- stem-level timbre analysis,
- source graph view with broad stems.

### Phase 3 — Source-Specific Harmonic Analysis

Goal: instrument-specific chord progression matching.

Required capabilities:

- detect likely pitched harmonic sources,
- run source-specific chord analysis,
- store source-specific chord events,
- search by source chord progression,
- search by chord-change timing,
- display confidence and caveats.

### Phase 4 — Correction Loop and Learning

Goal: improve practical usefulness through user feedback.

Required capabilities:

- source label correction,
- chord correction,
- relevant/irrelevant match feedback,
- correction-aware search ranking,
- correction-aware local source labeling.

### Phase 5 — Advanced Similarity and Production Features

Goal: deeper phenomenological matching.

Potential capabilities:

- production texture similarity,
- arrangement graph comparison,
- melody contour matching,
- vocal timbre matching,
- structural similarity,
- cross-song source role matching.

---

## 20. Acceptance Criteria by Phase

### Phase 1 Acceptance Criteria

The desktop MVP is acceptable when:

- user can import at least 100 local tracks,
- app can analyze imported tracks without freezing UI,
- user can select a track or clip,
- user can search by rhythm, harmony, timbre, and weighted combination,
- results show ranked matches with score breakdowns,
- original audio files remain untouched,
- failed files are reported without stopping the full batch.

### Phase 2 Acceptance Criteria

Broad stem phase is acceptable when:

- app can separate tracks into vocals, drums, bass, and other,
- app can search by drum similarity,
- app can search by bassline/root-motion similarity,
- app can search using accompaniment harmony separately from full mix,
- stem-level results identify matched stem and time range.

### Phase 3 Acceptance Criteria

Source-specific chord phase is acceptable when:

- app identifies likely pitched harmonic sources with confidence,
- app attempts chord analysis only on suitable sources by default,
- app stores source-specific chord events,
- user can search for similar instrument-specific chord progressions,
- results distinguish full-mix harmony from source-specific harmony,
- low-confidence chord matches are visually flagged.

---

## 21. Testing Strategy

### 21.1 Unit Tests

Test:

- data model creation,
- feature metadata versioning,
- score normalization,
- weighted scoring,
- chord token normalization,
- roman numeral conversion,
- candidate merging,
- correction override behavior.

### 21.2 Integration Tests

Test:

- import → analyze → index → search,
- full-mix feature extraction,
- stem analysis pipeline,
- source-specific analyzer routing,
- failed job recovery,
- stale feature invalidation,
- result explanation generation.

### 21.3 Evaluation Tests

Use curated test sets where expected similarity is known:

- same song in different keys,
- same progression at different tempos,
- same drums with different harmony,
- same harmony with different drums,
- same bassline with different instruments,
- similar guitar chords with different production,
- intentionally dissimilar tracks.

### 21.4 Manual QA Tests

Manual tests should verify:

- UI remains responsive during indexing,
- waveform and time selection are accurate,
- results are musically plausible,
- explanations are understandable,
- user corrections persist,
- cache deletion works,
- reanalysis updates stale features.

---

## 22. Evaluation Metrics

### 22.1 Retrieval Metrics

Use these metrics when a labeled evaluation set exists:

- precision at K,
- recall at K,
- mean reciprocal rank,
- normalized discounted cumulative gain,
- user relevance agreement.

### 22.2 Musical Diagnostics

Track these diagnostic measures:

- tempo estimation error,
- beat alignment quality,
- chord label agreement,
- roman numeral agreement,
- source label confidence distribution,
- false source-specific chord detections,
- query latency,
- indexing throughput.

### 22.3 User-Centric Metrics

Track locally, if telemetry is enabled by user:

- result accepted/rejected ratio,
- repeated searches per session,
- correction frequency by analyzer,
- dimensions most often used,
- dimensions most often disabled.

No telemetry should be enabled by default.

---

## 23. Error Handling and Confidence Policy

### 23.1 Error Handling

The system shall classify errors:

| Error Type | Example | Behavior |
|---|---|---|
| Decode error | unsupported file | Mark track failed; continue batch. |
| Model error | source separator crash | Store error; allow retry. |
| Feature error | chord extraction failed | Leave feature missing; continue other analyzers. |
| Index error | FAISS index write failed | Preserve database; rebuild index option. |
| File missing | user moved audio | Mark unavailable; preserve metadata. |

### 23.2 Confidence Display

The UI should use confidence bands:

| Confidence | Display |
|---|---|
| 0.80 to 1.00 | High confidence. |
| 0.60 to 0.79 | Medium confidence. |
| 0.40 to 0.59 | Low confidence. |
| < 0.40 | Very uncertain; hide from normal result explanations unless user enables diagnostics. |

### 23.3 Low-Confidence Rule

Low-confidence source and chord claims should be used cautiously in scoring and visibly marked in explanations.

---

## 24. Legal, Privacy, and Licensing Considerations

### 24.1 User Audio

The app should be designed for audio files the user has the right to process. It should not provide features intended to bypass DRM or acquire unauthorized music.

### 24.2 Local Processing

All analysis should be local by default. Any future cloud feature must require explicit user opt-in and clear disclosure.

### 24.3 Third-Party Libraries

Before commercial distribution, all third-party libraries, models, and datasets must receive licensing review. This includes source separation models, transcription models, audio analysis libraries, GUI libraries, packaging tools, and any evaluation datasets.

### 24.4 Cached Stems

Separated stems may be sensitive because they transform the original audio into derivative artifacts. The app should provide:

- option to disable stem artifact storage,
- option to store only features instead of audio stems,
- option to delete all cached stems,
- option to delete all analysis artifacts.

---

## 25. Security Considerations

- Treat imported file paths as untrusted input.
- Do not execute files from the music library.
- Sanitize metadata before display.
- Avoid loading arbitrary plugin code unless plugin signing or sandboxing exists.
- Store configuration and database files with normal user-level permissions.
- Keep model files in a controlled application data directory.
- Validate artifact paths before reading or deleting files.

---

## 26. Configuration

Required settings:

| Setting | Description |
|---|---|
| analysis_sample_rate | Sample rate for analysis. |
| max_parallel_jobs | Maximum concurrent analysis jobs. |
| stem_separation_enabled | Whether to run stem separation. |
| store_stem_audio | Whether to cache separated stems. |
| feature_storage_path | Where feature artifacts are stored. |
| index_storage_path | Where indices are stored. |
| model_storage_path | Where models are stored. |
| default_search_weights | Default similarity weights. |
| key_invariant_default | Whether harmonic searches normalize key by default. |
| tempo_invariant_default | Whether rhythm searches normalize tempo by default. |
| low_confidence_threshold | Threshold for warning or hiding uncertain claims. |

---

## 27. Development Roadmap

### Milestone A — Core Data and CLI

- Define data model.
- Implement import and metadata extraction.
- Implement full-mix feature extraction.
- Store features and metadata.
- Implement basic similarity search.

### Milestone B — Desktop MVP

- Implement PySide6 UI shell.
- Add library browser.
- Add waveform view.
- Add query clip selection.
- Add search controls.
- Add result ranking and explanation panel.

### Milestone C — Background Analysis

- Implement job queue.
- Implement progress reporting.
- Implement failure recovery.
- Implement reanalysis/version invalidation.

### Milestone D — Stem Layer

- Add source separation provider.
- Store broad stems.
- Add stem-level analysis.
- Add drum and bass search modes.

### Milestone E — Source Layer

- Add source graph model.
- Add sub-source discovery.
- Add source labeling.
- Add user source corrections.

### Milestone F — Instrument-Specific Harmony

- Add source-specific chord analyzer.
- Add source chord event storage.
- Add source chord search mode.
- Add source chord explanations.

### Milestone G — Feedback and Evaluation

- Add result feedback.
- Add correction-aware ranking.
- Add evaluation harness.
- Add curated test corpus.

---

## 28. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Source separation is imperfect | Wrong source-level analysis | Use confidence, corrections, broad fallback features. |
| Chord detection is noisy | Bad harmonic search | Use multiple evidence types: chroma, transcription, bass, confidence weighting. |
| Packaging Python ML desktop app is complex | Distribution friction | Start with developer build, then PyInstaller, then platform-specific installers. |
| Analysis is slow | Poor user experience | Background jobs, queue, caching, partial analysis, model toggles. |
| Too many features confuse users | Poor usability | Use simple presets and advanced controls hidden by default. |
| Similarity feels subjective | User distrust | Provide dimension sliders and result explanations. |
| Library grows large | Slow search/indexing | Use vector indices, segment manifests, and batch index updates. |
| Third-party model licensing | Release risk | Perform licensing review before commercial release. |

---

## 29. Recommended Initial Presets

### 29.1 Overall Similarity

```text
Rhythm: 25%
Harmony: 25%
Timbre: 25%
Production texture: 15%
Structure: 10%
```

### 29.2 Same Drums

```text
Drum groove: 55%
Drum timbre: 30%
Tempo: 15%
```

### 29.3 Same Chord Progression

```text
Roman numeral sequence: 50%
Chord-change timing: 25%
Root movement: 15%
Chord quality: 10%
```

### 29.4 Same Instrument-Specific Chords

```text
Source chord sequence: 40%
Chord-change timing: 20%
Voicing/articulation: 20%
Source timbre: 20%
```

### 29.5 Same Bassline

```text
Root motion: 35%
Pitch contour: 25%
Bass rhythm: 25%
Bass timbre: 15%
```

---

## 30. Minimal Technical Interfaces

### 30.1 Analyzer Interface

Every analyzer should behave as if it implements this contract:

```text
Analyzer
- name
- version
- supported_owner_types
- supported_source_types
- required_inputs
- produced_feature_types
- analyze(input_entity, context) -> AnalysisResult
```

### 30.2 Analysis Result

```text
AnalysisResult
- feature_views
- events
- artifacts
- warnings
- confidence
- provenance
```

### 30.3 Similarity Provider Interface

```text
SimilarityProvider
- feature_type
- supported_query_types
- retrieve_candidates(query, k) -> CandidateSet
- rerank(query, candidates) -> ScoreDetails
```

### 30.4 Explanation Object

```text
SearchExplanation
- combined_score
- dimension_scores
- matched_entities
- matched_time_ranges
- confidence_notes
- human_readable_summary
```

---

## 31. Glossary of Musical Analysis Concepts

| Concept | Explanation |
|---|---|
| Fourier transform | Mathematical decomposition of a signal into frequency components. |
| STFT | Short-time Fourier transform; frequency analysis over short windows. |
| CQT | Constant-Q transform; frequency representation useful for music because bins align better with pitch spacing. |
| Chroma | 12-dimensional pitch-class representation independent of octave. |
| MFCC | Mel-frequency cepstral coefficients; common timbre descriptors. |
| Tempogram | Representation of local rhythmic periodicity. |
| Beat-synchronous feature | Feature aligned to beat positions rather than fixed time intervals. |
| Roman numeral analysis | Key-normalized chord representation such as I, IV, V, vi. |
| Harmonic rhythm | Rate and timing of chord changes. |
| Source separation | Estimating component audio sources from a mixed recording. |
| Stem | Broad separated source group, such as vocals or drums. |
| Timbre | Perceived sound color or texture of an instrument/source. |
| Embedding | Numeric representation learned or engineered for similarity search. |
| Dynamic time warping | Sequence alignment method allowing local time stretching/compression. |

---

## 32. Open Questions

These should be resolved during prototype development:

1. Which chord detection approach gives the best practical tradeoff for full-mix vs source-specific analysis?
2. Should the app store separated stem audio by default, or only feature artifacts?
3. What is the smallest useful feature set for the first user-facing MVP?
4. How should the system calibrate confidence across unrelated analyzers?
5. What level of source discovery is acceptable before user correction becomes necessary?
6. Should the first release support Windows only, or Windows/macOS/Linux?
7. What licensing constraints apply to chosen separation and transcription models?
8. Should evaluation use open datasets, user-provided corpora, or both?
9. How should the app handle songs with tempo changes, live timing, or rubato?
10. Should search allow cross-instrument matches by default, such as guitar chords matching piano chords?

---

## 33. Recommended First Build

The first development build should not attempt everything. The fastest useful build is:

```text
Python desktop app
PySide6 UI
SQLite metadata database
Feature artifact folder
librosa full-mix features
FAISS vector search
Waveform display
Clip selection
Weighted rhythm/harmony/timbre search
Explainable result cards
```

Then add source-aware features in this order:

```text
1. Broad stem separation
2. Drum similarity
3. Bass root motion
4. Accompaniment harmony
5. Source graph
6. Source-specific chord analysis
7. User corrections
```

This order protects the project from overbuilding the hardest parts before the basic application loop works.

---

## 34. References for Implementation Research

The following references support the recommended implementation direction and should be reviewed during technical design:

- Qt for Python / PySide6 documentation: https://doc.qt.io/qtforpython-6/
- librosa feature extraction documentation: https://librosa.org/doc/0.11.0/feature.html
- Essentia music extractor documentation: https://essentia.upf.edu/streaming_extractor_music.html
- Demucs source separation project: https://github.com/facebookresearch/demucs
- Spotify Basic Pitch project: https://github.com/spotify/basic-pitch
- FAISS documentation: https://faiss.ai/index.html
- SQLite documentation: https://sqlite.org/about.html
- PyInstaller documentation: https://www.pyinstaller.org/
- FFmpeg documentation: https://ffmpeg.org/ffmpeg.html
- Python multiprocessing documentation: https://docs.python.org/3/library/multiprocessing.html
