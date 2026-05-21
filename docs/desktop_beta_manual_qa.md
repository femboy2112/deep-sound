# Desktop Beta Manual QA

Use this checklist for Phase 15 local beta testing and usability QA. Default automated verification stays dependency-light; the beta campaign records generated live QA, MIR quality, repo-dive, and toolset evidence, while installed PySide, CPU Demucs, and playback smoke remain optional host evidence. Optional-host outcomes are recorded with follow-up items; default Phase 15 closeout does not require fixing every optional-host failure.

## Setup

1. Prepare a tiny local audio folder with at least two valid audio files and one intentionally broken `.wav` text file.
2. Run `make bootstrap` if dependencies are missing.
3. Run `python3 scripts/status.py` and confirm `ACTIVE_PHASE: 15`.
4. Use a fresh library database, for example `/tmp/deep-sound-desktop-beta.sqlite`, and an app data directory under `/tmp/deep-sound-desktop-beta-data`.

## Beta Campaign Runner

1. Run the dependency-light campaign:

   ```bash
   python3 scripts/beta_campaign.py --fixture-mode generated --real-smoke-policy off --playback-smoke-policy off
   ```

2. Confirm `.build/beta_campaign_report.json` and `.build/beta_campaign_report.md` exist.
3. Confirm required campaign gates are recorded: verify, generated live QA, strict MIR quality, strict repo dive, and toolset review.
4. Confirm the report includes `schema_version`, `command`, `environment`, `dependency_policy`, `inputs`, `artifacts`, `required_gates`, `optional_gates`, `known_skips`, and `follow_up_items`.
5. When running on a prepared optional host, use `auto` policies to record installed PySide, Demucs, and playback outcomes without changing the default dependency-light contract.

## Live QA Harness

1. Run the dependency-light generated fixture gate:

   ```bash
   python3 scripts/live_qa.py --fixture-mode generated
   ```

2. Confirm `.build/live_qa_report.json` and `.build/live_qa_report.md` exist.
3. Confirm required gates are `passed`: import, analysis, index, search, waveform, clip, feedback, and artifact safety.
4. Confirm optional gates are listed separately as `skipped_optional` unless intentionally requested.
5. If an optional gate is requested and fails, keep the failure in the report with the command, fixture, and artifact context needed to reproduce it. Under `auto`, the failure is a follow-up item; under `required`, it is a blocking gate failure.
6. For closeout evidence on a machine with optional extras installed, run:

   ```bash
   QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py --fixture-mode generated --real-smoke-policy auto --playback-smoke-policy auto
   ```

7. Before closing a prepared-host optional smoke lane, run required real smoke only for dependencies that the host is intentionally expected to provide:

   ```bash
   QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py \
     --fixture-mode generated \
     --run-pyside-smoke \
     --run-demucs-smoke \
     --run-playback-smoke \
     --real-smoke-policy required \
     --playback-smoke-policy required
   ```

## MIR Quality Harness

1. Run the dependency-light generated quality gate:

   ```bash
   python3 scripts/mir_quality_eval.py --fixture-mode generated --strict
   ```

2. Confirm `.build/mir_quality_report.json` and `.build/mir_quality_report.md` exist.
3. Confirm all quality gates are `passed`: tempo stability, chroma/chord consistency, melody contour shape, drum groove proxy, bass motion proxy, quality-profile source routing, and confidence bounds.
4. Confirm the generated fixtures and derived app artifacts stay under `.build/` and the configured app data directory.
5. Confirm the `quality` profile does not require Demucs, PySide, playback, FAISS, GPU packages, learned models, cloud services, or the optional `[mir]` extra.
6. Treat the report as deterministic fixture evidence, not broad-corpus or real-separation quality proof.

## Manual Usability Report Format

Each live QA report includes `manual_usability_tasks` with:

- `task_id`
- `action`
- `expected_result`
- `observed_result`
- `status`: `passed`, `failed`, `blocked`, or `skipped_optional`
- `dependency_mode`
- `evidence_paths`
- `follow_up_recommendation`

Use this section to review operator scenarios, not as a replacement for the automated gates.

## Service Workflow

1. Import the folder through the desktop controller or CLI and confirm valid files import while the broken file records a failed job.
2. Analyze the library with profile `searchable`; confirm the aggregate job completes and per-track analysis state updates.
3. Analyze the same library with profile `quality`; confirm the aggregate job completes and adds deterministic full-mix, broad-stem, and source-owned quality feature rows.
4. Re-run the same analysis and confirm no duplicate feature errors.
5. Build the `searchable` and `quality` profile indexes and confirm index status DTOs show available backends or explicit scan caveats.
6. Run a track query and confirm result cards expose backend, dimension scores, stale-index warnings, caveats, and feedback action metadata.
7. Build a waveform cache for a selected track and confirm a JSON artifact is written under app data.
8. Select and persist a clip window; confirm the clip DTO has a `clip` query owner type and stable time bounds.
9. Submit relevant and irrelevant feedback on a result and confirm follow-up result DTOs expose feedback adjustment metadata.

## Interactive PySide Smoke

Only run this section after installing the `[ui]` extra. For harness evidence, request it explicitly with `QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py --fixture-mode generated --run-pyside-smoke --real-smoke-policy required`.

1. Create the desktop app window with a fresh database and confirm the main-window import, analyze, reindex, refresh, and selected-track search buttons route through the injected controller.
2. Select a track row, build a waveform cache, and confirm the track-detail panel shows selected-track state plus waveform or an explicit cache-unavailable message.
3. Select and persist a clip window, materialize clip-owned rhythm, harmony, and timbre features, then run a clip query.
4. Open the query builder and confirm track, clip, and compatible source modes produce enabled search intents only when validation passes.
5. Inspect result cards and confirm preview, compare, relevant, and irrelevant actions are available only when query/result owner ids are present.
6. Inspect the source graph and confirm source detail, correction controls, and compatible source-search actions are exposed only for compatible source types.
7. Confirm source, chord, event, and result language remains caveated/probabilistic and no result is presented as a definitive match.

## Optional Playback Smoke

Only run this section after intentionally installing the `[playback]` extra and confirming the host has a usable local output device. Default verification must not open an audio device.

1. Install or restore the optional environment:

   ```bash
   uv sync --extra ui --extra playback
   ```

2. Run the generated live QA playback gate in auto mode:

   ```bash
   python3 scripts/live_qa.py --fixture-mode generated --playback-smoke-policy auto
   ```

3. On a prepared machine where playback output is expected, run the required gate:

   ```bash
   DEEP_SOUND_RUN_PLAYBACK_SMOKE=1 uv run pytest tests/test_phase13_live_playback_smoke.py -vv
   python3 scripts/live_qa.py --fixture-mode generated --run-playback-smoke --playback-smoke-policy required
   ```

4. Confirm the report records `playback_smoke` separately from required gates, generated audio is used, playback stops immediately, and the generated fixture hash remains unchanged.

## Optional Real-Source Smoke

Only run this section after intentionally installing the `[demucs]` extra or otherwise making the `demucs` executable available. The default project path is CPU-only Torch/Torchaudio through the `pytorch-cpu` uv index; do not add CUDA/NVIDIA/Triton packages for Phase 12.

1. Install or restore the optional environment:

   ```bash
   uv sync --extra ui --extra demucs
   ```

2. Run the Phase 11 real workflow smoke. The test generates a tiny deterministic fixture when `DEEP_SOUND_DEMUCS_SMOKE_AUDIO` is not supplied:

   ```bash
   DEEP_SOUND_RUN_DEMUCS_SMOKE=1 uv run pytest tests/test_phase11_live_demucs_workflow.py -vv
   ```

3. Confirm `uv.lock` contains no `nvidia-*`, CUDA, or `triton` package names for the default CPU Demucs path.
4. Run the CLI opt-in path:

   ```bash
   uv run deep-sound analyze-library \
     --library-db /tmp/deep-sound-real-source.sqlite \
     --import-path /path/to/tiny.wav \
     --profile source_aware_real \
     --app-data-dir /tmp/deep-sound-real-source-data
   ```

5. Confirm stems are written below `/tmp/deep-sound-real-source-data/stems/`, original audio bytes are unchanged, and persisted stem metadata reports `demucs` with model/version/params/input provenance.
6. Run the same command with an intentionally missing `--demucs-executable` and confirm the CLI fails with a clear `source_aware_real` opt-in error.
7. For harness evidence, request the optional gate explicitly. `scripts/live_qa.py` generates a Demucs smoke fixture when `--demucs-audio` is omitted:

   ```bash
   QT_QPA_PLATFORM=offscreen python3 scripts/live_qa.py \
     --fixture-mode generated \
     --run-demucs-smoke \
     --real-smoke-policy required
   ```

## Known Gaps

- Playback output is beta-only and depends on host audio-device availability.
- Default verification does not exercise a real installed PySide session unless `[ui]` is installed locally.
- Default `source_aware` QA still uses fake-provider source paths. Real separation QA uses only the explicit `source_aware_real` path.
- Generated MIR quality evidence does not prove broad-corpus or production separation quality.
- Optional live gate skips are expected when dependencies are absent under `auto`, and requested optional failures must remain visible in `.build/live_qa_report.*` and campaign follow-up items.

## Non-Goals

- Do not install Demucs, playback, FAISS, or heavy MIR extras for default desktop beta QA.
- Do not add a CUDA/GPU Demucs path in Phase 15.
- Do not modify original audio files.
- Do not treat fake-provider source-aware output as production separation quality.
