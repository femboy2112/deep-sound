# Architecture — distilled

Source: [`SPEC.md` §10](SPEC.md).

## High-level layering

```
Desktop UI (PySide6)
    ↓
Application Controller
    ↓
Domain Services
    ├── Library Service          (file import, metadata, dedupe, status)
    ├── Analysis Service         (orchestrates feature extraction + model inference)
    ├── Source Service           (stems, detected sources, labels, activity)
    ├── Feature Service          (vectors, symbolic sequences, events)
    ├── Similarity Service       (candidate retrieval + reranking)
    ├── Explanation Service      (score breakdowns → human-readable summaries)
    ├── Playback Service         (audio playback inside the app)
    └── Correction Service       (user overrides, label edits, feedback)
    ↓
Infrastructure
    ├── Audio Decoder            (ffmpeg/soundfile)
    ├── Model Runtime            (librosa, demucs, basic-pitch, embedding models)
    ├── Job Queue                (background workers, progress, cancel)
    ├── SQLite Metadata Store    (library.sqlite)
    ├── Feature Artifact Store   (compressed numpy arrays under features/)
    ├── Vector Index Store       (FAISS indices under indices/)
    └── Configuration Store      (settings.json)
```

## Service boundaries (hard rule)

Cross-service calls go through public interfaces. A service never reaches into another's internals. The picker enforces this via FILE_PLAN dependency declarations.

## Processing boundary

Long-running operations (decode, stem separation, source discovery, chord inference, index build, search rerank) MUST run outside the UI thread. Use the Job Queue.

## Plugin boundary

The MVP is Python, but every analyzer and similarity provider implements a small interface (see spec §30) so a future native (C++/Rust) implementation can be dropped in.
