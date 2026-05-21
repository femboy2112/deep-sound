# Desktop Beta Manual QA

Use this checklist for Phase 11 local desktop beta QA. Default automated verification stays dependency-light; live PySide, real-Demucs, and local audio-device checks are explicit opt-in gates and must be logged separately from required generated-fixture evidence.

## Setup

1. Prepare a tiny local audio folder with at least two valid audio files and one intentionally broken `.wav` text file.
2. Run `make bootstrap` if dependencies are missing.
3. Run `python3 scripts/status.py` and confirm `ACTIVE_PHASE: 11`.
4. Use a fresh library database, for example `/tmp/deep-sound-desktop-beta.sqlite`, and an app data directory under `/tmp/deep-sound-desktop-beta-data`.

## Live QA Harness

1. Run the dependency-light generated fixture gate:

   ```bash
   python3 scripts/live_qa.py --fixture-mode generated
   ```

2. Confirm `.build/live_qa_report.json` and `.build/live_qa_report.md` exist.
3. Confirm required gates are `passed`: import, analysis, index, search, waveform, clip, feedback, and artifact safety.
4. Confirm optional gates are listed separately as `skipped_optional` unless intentionally requested.
5. If an optional gate is requested and fails, keep the failure in the report with the command, fixture, and artifact context needed to reproduce it. Do not rewrite the failure as a skip.

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

Only run this section after installing the `[ui]` extra. For harness evidence, request it explicitly with `python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke`.

1. Create the desktop app window with a fresh database and confirm the main-window import, analyze, reindex, refresh, and selected-track search buttons route through the injected controller.
2. Select a track row, build a waveform cache, and confirm the track-detail panel shows selected-track state plus waveform or an explicit cache-unavailable message.
3. Select and persist a clip window, materialize clip-owned rhythm, harmony, and timbre features, then run a clip query.
4. Open the query builder and confirm track, clip, and compatible source modes produce enabled search intents only when validation passes.
5. Inspect result cards and confirm preview, compare, relevant, and irrelevant actions are available only when query/result owner ids are present.
6. Inspect the source graph and confirm source detail, correction controls, and compatible source-search actions are exposed only for compatible source types.
7. Confirm source, chord, event, and result language remains caveated/probabilistic and no result is presented as a definitive match.

## Optional Real-Source Smoke

Only run this section after intentionally installing the `[demucs]` extra or otherwise making the `demucs` executable available.

1. Prepare one tiny local audio fixture and confirm it is safe to copy into temporary app data.
2. Run `DEEP_SOUND_RUN_DEMUCS_SMOKE=1 DEEP_SOUND_DEMUCS_SMOKE_AUDIO=/path/to/tiny.wav uv run pytest tests/test_phase10_optional_demucs_smoke.py`.
3. Run the CLI opt-in path:

   ```bash
   uv run deep-sound analyze-library \
     --library-db /tmp/deep-sound-real-source.sqlite \
     --import-path /path/to/tiny.wav \
     --profile source_aware_real \
     --app-data-dir /tmp/deep-sound-real-source-data
   ```

4. Confirm stems are written below `/tmp/deep-sound-real-source-data/stems/`, original audio bytes are unchanged, and persisted stem metadata reports `demucs` with model/version/params/input provenance.
5. Run the same command with an intentionally missing `--demucs-executable` and confirm the CLI fails with a clear `source_aware_real` opt-in error.
6. For harness evidence, request the optional gate explicitly:

   ```bash
   python3 scripts/live_qa.py \
     --fixture-mode generated \
     --run-demucs-smoke \
     --demucs-audio /path/to/tiny.wav
   ```

## Known Gaps

- Playback transport controls are still UI placeholders.
- Default verification does not exercise a real installed PySide session unless `[ui]` is installed locally.
- Default `source_aware` QA still uses fake-provider source paths. Real separation QA uses only the explicit `source_aware_real` path.
- Optional live gate skips are expected when dependencies or fixtures are absent, but requested gate failures must remain visible in `.build/live_qa_report.*`.

## Non-Goals

- Do not install Demucs, FAISS, or heavy MIR extras for default desktop beta QA.
- Do not modify original audio files.
- Do not treat fake-provider source-aware output as production separation quality.
