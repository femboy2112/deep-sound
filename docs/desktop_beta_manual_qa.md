# Desktop Beta Manual QA

Use this checklist for Phase 9 local desktop beta QA. Default automated verification stays dependency-light; PySide checks are manual or skipped unless the `[ui]` extra is installed.

## Setup

1. Prepare a tiny local audio folder with at least two valid audio files and one intentionally broken `.wav` text file.
2. Run `make bootstrap` if dependencies are missing.
3. Run `python3 scripts/status.py` and confirm `ACTIVE_PHASE: 9`.
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

## Interactive PySide Smoke

Only run this section after installing the `[ui]` extra.

1. Create the desktop app window with a fresh database and confirm the main-window import, analyze, reindex, refresh, and selected-track search buttons route through the injected controller.
2. Select a track row, build a waveform cache, and confirm the track-detail panel shows selected-track state plus waveform or an explicit cache-unavailable message.
3. Select and persist a clip window, materialize clip-owned rhythm, harmony, and timbre features, then run a clip query.
4. Open the query builder and confirm track, clip, and compatible source modes produce enabled search intents only when validation passes.
5. Inspect result cards and confirm preview, compare, relevant, and irrelevant actions are available only when query/result owner ids are present.
6. Inspect the source graph and confirm source detail, correction controls, and compatible source-search actions are exposed only for compatible source types.
7. Confirm source, chord, event, and result language remains caveated/probabilistic and no result is presented as a definitive match.

## Known Gaps

- Playback transport controls are still UI placeholders.
- Default verification does not exercise a real installed PySide session unless `[ui]` is installed locally.
- Source-aware QA still uses fake-provider source paths unless the optional Demucs extra is installed intentionally.

## Non-Goals

- Do not install Demucs, FAISS, or heavy MIR extras for default desktop beta QA.
- Do not modify original audio files.
- Do not treat fake-provider source-aware output as production separation quality.
