# Desktop Beta Manual QA

Use this checklist for Phase 8 local desktop beta QA. Default automated verification stays dependency-light; PySide checks are manual or skipped unless the `[ui]` extra is installed.

## Setup

1. Prepare a tiny local audio folder with at least two valid audio files and one intentionally broken `.wav` text file.
2. Run `make bootstrap` if dependencies are missing.
3. Run `python3 scripts/status.py` and confirm `ACTIVE_PHASE: 8`.
4. Use a fresh library database, for example `/tmp/deep-sound-desktop-beta.sqlite`, and an app data directory under `/tmp/deep-sound-desktop-beta-data`.

## Service Workflow

1. Import the folder through the desktop controller or CLI and confirm valid files import while the broken file records a failed job.
2. Analyze the library with profile `searchable`; confirm the aggregate job completes and per-track analysis state updates.
3. Re-run the same analysis and confirm no duplicate feature errors.
4. Build the `searchable` profile indexes and confirm index status DTOs show available backends or explicit scan caveats.
5. Run a track query and confirm result cards expose backend, dimension scores, stale-index warnings, caveats, and feedback action metadata.
6. Build a waveform cache for a selected track and confirm a JSON artifact is written under app data.
7. Select and persist a clip window; confirm the clip DTO has a `clip` query owner type and stable time bounds.
8. Submit relevant and irrelevant feedback on a result and confirm follow-up result DTOs expose feedback adjustment metadata.

## Optional PySide Smoke

Only run this section after installing the `[ui]` extra.

1. Create the main window and confirm import/analyze/index/search actions map to workflow intent DTOs.
2. Open the query builder and confirm track, clip, and compatible source modes produce the expected query state.
3. Open waveform, result, and source detail panels and confirm no PySide import is needed before widget factories are called.
4. Confirm source and chord labels remain caveated/probabilistic and no result is presented as a definitive match.

## Non-Goals

- Do not install Demucs, FAISS, or heavy MIR extras for default desktop beta QA.
- Do not modify original audio files.
- Do not treat fake-provider source-aware output as production separation quality.
