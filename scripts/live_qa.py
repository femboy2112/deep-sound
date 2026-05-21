"""Run non-mutating live beta QA and write structured evidence reports."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

try:
    import numpy as np
    import soundfile as sf
except ModuleNotFoundError:
    if __name__ != "__main__" or os.environ.get("DEEP_SOUND_LIVE_QA_REEXEC") == "1":
        raise
    env = os.environ.copy()
    env["DEEP_SOUND_LIVE_QA_REEXEC"] = "1"
    os.execvpe("uv", ["uv", "run", "python3", str(Path(__file__).resolve()), *sys.argv[1:]], env)

from report_contracts import (
    SCHEMA_VERSION,
    command_metadata,
    dependency_policy,
    follow_up_items_from_gates,
    known_skips_from_gates,
    runtime_environment,
)

from deep_sound.domain.corrections import ResultFeedbackValue
from deep_sound.domain.feature_view import OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.clip_analysis_service import ClipAnalysisService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SimilarityService
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    ClipSelectionIntentDTO,
    DesktopWorkflowController,
    FeedbackIntentDTO,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
    WaveformIntentDTO,
)

BUILD_DIR = REPO_ROOT / ".build"
JSON_REPORT_PATH = BUILD_DIR / "live_qa_report.json"
MD_REPORT_PATH = BUILD_DIR / "live_qa_report.md"


@dataclass(frozen=True, slots=True)
class GateResult:
    name: str
    status: str
    optional: bool = False
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UsabilityTaskResult:
    task_id: str
    action: str
    expected_result: str
    observed_result: str
    status: str
    dependency_mode: str
    evidence_paths: list[str] = field(default_factory=list)
    follow_up_recommendation: str = ""


@dataclass(frozen=True, slots=True)
class LiveQAReport:
    schema_version: str
    command: list[str]
    environment: dict[str, Any]
    dependency_policy: dict[str, Any]
    inputs: dict[str, Any]
    artifacts: dict[str, str]
    timestamp: str
    overall: str
    fixture_mode: str
    run_dir: str
    app_data_dir: str
    required_gates: list[GateResult]
    optional_gates: list[GateResult]
    known_skips: list[dict[str, str]]
    follow_up_items: list[dict[str, str]]
    manual_usability_tasks: list[UsabilityTaskResult] = field(default_factory=list)


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_click_track(path: Path, *, bpm: float) -> None:
    sample_rate = 22_050
    duration_sec = 3.0
    period_sec = 60.0 / bpm
    samples = np.zeros(int(sample_rate * duration_sec), dtype=np.float32)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float32)
    t = 0.0
    while t < duration_sec:
        start = int(t * sample_rate)
        end = min(start + click_len, samples.shape[0])
        samples[start:end] += envelope[: end - start]
        t += period_sec
    sf.write(path, samples, sample_rate)


def _write_demucs_smoke_fixture(path: Path) -> None:
    sample_rate = 22_050
    duration_sec = 2.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    bass = 0.22 * np.sin(2.0 * np.pi * 82.41 * t)
    chord = 0.12 * (
        np.sin(2.0 * np.pi * 261.63 * t)
        + np.sin(2.0 * np.pi * 329.63 * t)
        + np.sin(2.0 * np.pi * 392.00 * t)
    )
    click = np.zeros_like(t)
    click_len = int(0.015 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len)).astype(np.float64)
    for beat in (0.0, 0.5, 1.0, 1.5):
        start = int(beat * sample_rate)
        end = min(start + click_len, click.shape[0])
        click[start:end] += 0.35 * envelope[: end - start]
    audio = np.clip(bass + chord + click, -0.9, 0.9).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sample_rate)


def _write_playback_smoke_fixture(path: Path) -> None:
    sample_rate = 22_050
    duration_sec = 0.20
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (0.05 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, audio, sample_rate)


def _prepare_generated_fixtures(run_dir: Path) -> tuple[Path, list[Path], Path]:
    fixture_dir = run_dir / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    audio_paths = [
        fixture_dir / "query_song.wav",
        fixture_dir / "near_song.wav",
    ]
    _write_click_track(audio_paths[0], bpm=120.0)
    _write_click_track(audio_paths[1], bpm=124.0)
    broken_path = fixture_dir / "broken.wav"
    broken_path.write_text("not a valid wav file\n", encoding="utf-8")
    return fixture_dir, audio_paths, broken_path


def _run_required_generated(run_dir: Path) -> list[GateResult]:
    fixture_dir, audio_paths, broken_path = _prepare_generated_fixtures(run_dir)
    original_hashes = {str(path): _sha256_file(path) for path in (*audio_paths, broken_path)}
    app_data_dir = run_dir / "app_data"
    store = SqliteStore(run_dir / "library.sqlite")
    store.init_schema()
    controller = DesktopWorkflowController(store, app_data_dir=app_data_dir)

    gates: list[GateResult] = []

    import_job = controller.import_paths(ImportIntentDTO(paths=(fixture_dir,)))
    tracks = store.list_tracks()
    failed_imports = [
        job for job in store.list_jobs() if job.job_type == "import_file" and job.status == "failed"
    ]
    _require(import_job.status == "completed", "generated fixture import job failed")
    _require(len(tracks) == 2, f"expected 2 imported tracks, got {len(tracks)}")
    _require(len(failed_imports) == 1, "expected the broken wav to be recorded as a failed import")
    gates.append(
        GateResult(
            name="import",
            status="passed",
            summary="Imported generated valid audio and recorded the broken wav as a failed job.",
            details={
                "track_count": len(tracks),
                "failed_import_count": len(failed_imports),
                "fixture_dir": str(fixture_dir),
            },
        )
    )

    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    _require(analyze_job.status == "completed", "searchable analysis failed")
    feature_service = FeatureService(store)
    first_feature_count = _feature_count(feature_service)
    rerun_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    second_feature_count = _feature_count(feature_service)
    _require(rerun_job.status == "completed", "searchable analysis rerun failed")
    _require(
        first_feature_count == second_feature_count, "analysis rerun changed feature row count"
    )
    gates.append(
        GateResult(
            name="analysis",
            status="passed",
            summary="Searchable analysis completed and reran idempotently.",
            details={
                "profile": AnalysisProfile.SEARCHABLE.value,
                "feature_count": second_feature_count,
            },
        )
    )

    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    snapshot = controller.snapshot()
    _require(index_job.status == "completed", "profile indexing failed")
    _require(snapshot.index_statuses, "no index statuses were produced")
    _require(
        all(status.available for status in snapshot.index_statuses),
        "one or more profile indexes are unavailable",
    )
    gates.append(
        GateResult(
            name="index",
            status="passed",
            summary="Built searchable profile indexes and captured available index statuses.",
            details={
                "index_statuses": [
                    {
                        "feature_type": status.feature_type,
                        "owner_type": status.owner_type,
                        "backend": status.backend,
                        "feature_count": status.feature_count,
                        "stale": status.stale,
                    }
                    for status in snapshot.index_statuses
                ],
            },
        )
    )

    query_track = next(track for track in tracks if track.title == "query_song")
    results = controller.search(SearchIntentDTO(query_id=query_track.id, mode="rhythm", top_k=1))
    _require(results, "search produced no results")
    gates.append(
        GateResult(
            name="search",
            status="passed",
            summary="Ran a rhythm search and preserved backend and dimension-score evidence.",
            details={
                "query_id": query_track.id,
                "result_count": len(results),
                "top_result_owner_id": results[0].result_owner_id,
                "top_score": results[0].combined_score,
                "backend": results[0].search_backend,
                "dimension_scores": results[0].dimension_scores,
            },
        )
    )

    waveform_job, waveform = controller.build_waveform(
        WaveformIntentDTO(track_id=query_track.id, point_count=64)
    )
    _require(waveform_job.status == "completed", "waveform cache job failed")
    _require(waveform.artifact_path.is_file(), "waveform artifact was not written")
    _require(_is_relative_to(waveform.artifact_path, app_data_dir), "waveform escaped app data dir")
    gates.append(
        GateResult(
            name="waveform",
            status="passed",
            summary="Built waveform cache artifact under app data.",
            details={
                "artifact_path": str(waveform.artifact_path),
                "point_count": len(waveform.points),
                "algorithm": waveform.algorithm,
                "version": waveform.version,
            },
        )
    )

    clip, clip_query = controller.create_clip_selection(
        ClipSelectionIntentDTO(
            track_id=query_track.id,
            start_sec=0.0,
            end_sec=1.2,
            label="live-qa-hook",
        )
    )
    clip_result = ClipAnalysisService(store, app_data_dir=app_data_dir).analyze_clip(clip.id)
    clip_results = SimilarityService(FeatureService(store)).search(
        clip_query.query_owner_id,
        {"rhythm": 1.0},
        top_k=1,
        owner_type=OwnerType.TRACK,
    )
    _require(clip_result.artifact_path.is_file(), "clip artifact was not written")
    _require(_is_relative_to(clip_result.artifact_path, app_data_dir), "clip escaped app data dir")
    _require(len(clip_result.feature_views) == 3, "clip feature materialization incomplete")
    _require(clip_results, "clip-owned search produced no results")
    gates.append(
        GateResult(
            name="clip",
            status="passed",
            summary="Persisted a clip window, materialized clip-owned features, and searched from it.",
            details={
                "clip_id": clip.id,
                "artifact_path": str(clip_result.artifact_path),
                "feature_count": len(clip_result.feature_views),
                "result_count": len(clip_results),
            },
        )
    )

    feedback_job = controller.submit_feedback(
        FeedbackIntentDTO(
            query_owner_id=query_track.id,
            result_owner_id=results[0].result_owner_id,
            value=ResultFeedbackValue.RELEVANT,
        )
    )
    _require(feedback_job.status == "completed", "feedback job failed")
    gates.append(
        GateResult(
            name="feedback",
            status="passed",
            summary="Recorded relevant feedback through the desktop controller.",
            details={
                "query_owner_id": query_track.id,
                "result_owner_id": results[0].result_owner_id,
                "value": ResultFeedbackValue.RELEVANT.value,
            },
        )
    )

    final_hashes = {str(path): _sha256_file(path) for path in (*audio_paths, broken_path)}
    _require(final_hashes == original_hashes, "one or more original fixture files changed")
    gates.append(
        GateResult(
            name="artifact_safety",
            status="passed",
            summary="Original audio fixture bytes were unchanged; generated artifacts stayed under app data.",
            details={
                "original_hashes": original_hashes,
                "app_data_dir": str(app_data_dir),
                "artifact_paths": [
                    str(waveform.artifact_path),
                    str(clip_result.artifact_path),
                ],
            },
        )
    )

    return gates


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _feature_count(feature_service: FeatureService) -> int:
    from deep_sound.services.index_service import INDEX_PROFILE_FEATURES

    return sum(
        len(feature_service.list_by_type(feature_type, owner_type=owner_type))
        for owner_type, feature_type in INDEX_PROFILE_FEATURES[AnalysisProfile.SEARCHABLE]
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _optional_pyside_gate(*, run: bool, required: bool, run_dir: Path) -> GateResult:
    if not run:
        return GateResult(
            name="pyside_smoke",
            status="skipped_optional",
            optional=True,
            summary="PySide smoke was not requested.",
        )
    if find_spec("PySide6") is None:
        status = "failed" if required else "skipped_optional"
        return GateResult(
            name="pyside_smoke",
            status=status,
            optional=True,
            summary="PySide smoke is required but PySide6 is not installed."
            if required
            else "PySide smoke was requested but PySide6 is not installed.",
        )
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from deep_sound.ui.desktop_app import (
            create_desktop_app_window,
            desktop_app_config,
        )

        window = create_desktop_app_window(
            desktop_app_config(
                run_dir / "pyside_smoke.sqlite",
                app_data_dir=run_dir / "pyside_app_data",
            ),
            argv=("deep-sound-live-qa",),
        )
    except Exception as exc:
        return GateResult(
            name="pyside_smoke",
            status="failed",
            optional=True,
            summary="PySide smoke import failed.",
            details={"error": str(exc)},
        )
    return GateResult(
        name="pyside_smoke",
        status="passed",
        optional=True,
        summary="PySide desktop app/window factory succeeded.",
        details={
            "library_db_path": str(window.bootstrap.config.library_db_path),
            "app_data_dir": str(window.bootstrap.config.app_data_dir),
        },
    )


def _optional_demucs_gate(
    args: argparse.Namespace,
    *,
    run: bool,
    required: bool,
    run_dir: Path,
) -> GateResult:
    if not run:
        return GateResult(
            name="real_source_smoke",
            status="skipped_optional",
            optional=True,
            summary="Real Demucs source-aware smoke was not requested.",
        )
    executable_name = str(args.demucs_executable or "demucs")
    executable = shutil.which(executable_name)
    if executable is None:
        status = "failed" if required else "skipped_optional"
        return GateResult(
            name="real_source_smoke",
            status=status,
            optional=True,
            summary="Real Demucs source-aware smoke is required but Demucs is not installed."
            if required
            else "Real Demucs source-aware smoke was requested but Demucs is not installed.",
        )
    audio_path = args.demucs_audio.expanduser() if args.demucs_audio is not None else None
    if audio_path is None:
        audio_path = run_dir / "fixtures" / "generated_demucs_smoke.wav"
        _write_demucs_smoke_fixture(audio_path)
    if not audio_path.is_file():
        status = "failed" if required else "skipped_optional"
        return GateResult(
            name="real_source_smoke",
            status=status,
            optional=True,
            summary=f"Real Demucs source-aware smoke fixture is not a file: {audio_path}",
        )

    env = os.environ.copy()
    env["DEEP_SOUND_RUN_DEMUCS_SMOKE"] = "1"
    env["DEEP_SOUND_DEMUCS_SMOKE_AUDIO"] = str(audio_path)
    env["DEEP_SOUND_DEMUCS_EXECUTABLE"] = executable
    env.setdefault("UV_CACHE_DIR", "/tmp/uv-cache")
    env.setdefault("TORCH_HOME", str(run_dir / "torch_cache"))
    env.setdefault("XDG_CACHE_HOME", str(run_dir / "xdg_cache"))
    argv = [
        "uv",
        "run",
        "pytest",
        "tests/test_phase11_live_demucs_workflow.py",
        "-vv",
    ]
    proc = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=args.optional_timeout_sec,
    )
    status = "passed" if proc.returncode == 0 else "failed"
    if proc.returncode == 5 or "skipped" in proc.stdout.lower():
        status = "skipped_optional"
    if required and status == "skipped_optional":
        status = "failed"
    return GateResult(
        name="real_source_smoke",
        status=status,
        optional=True,
        summary="Ran requested real Demucs source-aware smoke command.",
        details={
            "argv": argv,
            "audio_path": str(audio_path),
            "run_dir": str(run_dir),
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        },
    )


def _playback_output_available() -> bool:
    if find_spec("sounddevice") is None:
        return False
    try:
        sd = import_module("sounddevice")
        devices = sd.query_devices()  # type: ignore[attr-defined]
    except Exception:
        return False
    if isinstance(devices, dict):
        return int(devices.get("max_output_channels", 0)) > 0
    return any(int(device.get("max_output_channels", 0)) > 0 for device in devices)


def _optional_playback_gate(*, run: bool, required: bool, run_dir: Path) -> GateResult:
    if not run:
        return GateResult(
            name="playback_smoke",
            status="skipped_optional",
            optional=True,
            summary="Playback smoke was not requested or no output-capable device was detected.",
        )
    if find_spec("sounddevice") is None:
        status = "failed" if required else "skipped_optional"
        return GateResult(
            name="playback_smoke",
            status=status,
            optional=True,
            summary="Playback smoke is required but sounddevice is not installed."
            if required
            else "Playback smoke was requested but sounddevice is not installed.",
        )
    if not _playback_output_available():
        status = "failed" if required else "skipped_optional"
        return GateResult(
            name="playback_smoke",
            status=status,
            optional=True,
            summary="Playback smoke is required but no output-capable device was detected."
            if required
            else "Playback smoke skipped because no output-capable device was detected.",
        )

    from deep_sound.domain.track import Track
    from deep_sound.services.playback_service import (
        LocalPlaybackAdapter,
        PlaybackRequest,
        PlaybackStatus,
    )

    audio_path = run_dir / "fixtures" / "generated_playback_smoke.wav"
    _write_playback_smoke_fixture(audio_path)
    before_hash = _sha256_file(audio_path)
    adapter = LocalPlaybackAdapter(audio_output_enabled=True)
    try:
        state = adapter.play(
            PlaybackRequest(
                Track(id="playback-smoke", filepath=audio_path, duration_sec=0.20),
                position_sec=0.0,
            )
        )
        stopped = adapter.stop()
    except Exception as exc:
        return GateResult(
            name="playback_smoke",
            status="failed",
            optional=True,
            summary="Playback smoke raised an unexpected error.",
            details={"error": str(exc), "audio_path": str(audio_path)},
        )
    after_hash = _sha256_file(audio_path)
    passed = (
        state.status is PlaybackStatus.PLAYING
        and state.is_output_active
        and stopped.status is PlaybackStatus.STOPPED
        and before_hash == after_hash
    )
    return GateResult(
        name="playback_smoke",
        status="passed" if passed else "failed",
        optional=True,
        summary="Generated audio played nonblocking and stopped immediately."
        if passed
        else "Generated audio playback failed or modified the fixture.",
        details={
            "audio_path": str(audio_path),
            "backend": state.backend,
            "play_status": state.status.value,
            "stop_status": stopped.status.value,
            "output_active": state.is_output_active,
            "fixture_unchanged": before_hash == after_hash,
            "error": state.error_message,
        },
    )


def _report_overall(
    required: list[GateResult],
    optional: list[GateResult],
    *,
    required_optional_names: set[str],
) -> str:
    failures = [gate for gate in required if gate.status == "failed"]
    failures.extend(
        gate
        for gate in optional
        if gate.status == "failed" and gate.name in required_optional_names
    )
    return "fail" if failures else "pass"


def _manual_usability_tasks(
    required: list[GateResult],
    optional: list[GateResult],
    *,
    run_dir: Path,
) -> list[UsabilityTaskResult]:
    gate_by_name = {gate.name: gate for gate in (*required, *optional)}
    task_specs = [
        (
            "U-IMPORT",
            "Import a generated folder containing valid audio and one broken file.",
            "Valid files appear in the library and the broken file is recorded as a failed job.",
            "import",
            "required",
        ),
        (
            "U-ANALYZE-INDEX",
            "Analyze and index the generated library.",
            "The searchable profile completes, reruns idempotently, and index statuses are available.",
            "index",
            "required",
        ),
        (
            "U-SEARCH",
            "Run a library search from the generated query track.",
            "Results include backend and dimension-score evidence.",
            "search",
            "required",
        ),
        (
            "U-WAVEFORM-CLIP",
            "Build a waveform cache, select a clip, and search from clip-owned features.",
            "Waveform and clip artifacts stay under app data and clip search returns results.",
            "clip",
            "required",
        ),
        (
            "U-FEEDBACK",
            "Submit relevant feedback for the top generated result.",
            "Feedback is recorded through the desktop controller.",
            "feedback",
            "required",
        ),
        (
            "U-PYSIDE",
            "Open the optional PySide desktop smoke when the UI extra is available.",
            "Window creation passes or records an optional dependency skip.",
            "pyside_smoke",
            "optional",
        ),
        (
            "U-PLAYBACK",
            "Run the optional playback smoke under the selected playback policy.",
            "Playback passes, fails, or records an optional dependency/device skip.",
            "playback_smoke",
            "optional",
        ),
    ]
    tasks: list[UsabilityTaskResult] = []
    for task_id, action, expected, gate_name, dependency_mode in task_specs:
        gate = gate_by_name.get(gate_name)
        if gate is None:
            tasks.append(
                UsabilityTaskResult(
                    task_id=task_id,
                    action=action,
                    expected_result=expected,
                    observed_result="No matching gate was recorded.",
                    status="blocked",
                    dependency_mode=dependency_mode,
                    evidence_paths=[str(run_dir)],
                    follow_up_recommendation="Record this scenario in live QA before closeout.",
                )
            )
            continue
        follow_up = "" if gate.status == "passed" else gate.summary
        tasks.append(
            UsabilityTaskResult(
                task_id=task_id,
                action=action,
                expected_result=expected,
                observed_result=gate.summary,
                status=gate.status,
                dependency_mode=dependency_mode,
                evidence_paths=[str(run_dir), str(JSON_REPORT_PATH), str(MD_REPORT_PATH)],
                follow_up_recommendation=follow_up,
            )
        )
    return tasks


def _write_reports(report: LiveQAReport) -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    payload = asdict(report)
    JSON_REPORT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    MD_REPORT_PATH.write_text(_markdown_report(report), encoding="utf-8")


def _markdown_report(report: LiveQAReport) -> str:
    lines = [
        "# Live QA Report",
        "",
        f"- Timestamp: `{report.timestamp}`",
        f"- Overall: `{report.overall}`",
        f"- Fixture mode: `{report.fixture_mode}`",
        f"- Run dir: `{report.run_dir}`",
        f"- App data dir: `{report.app_data_dir}`",
        "",
        "## Required Gates",
        "",
        "| Gate | Status | Summary |",
        "|---|---|---|",
    ]
    for gate in report.required_gates:
        lines.append(f"| `{gate.name}` | `{gate.status}` | {gate.summary} |")
    lines.extend(
        [
            "",
            "## Optional Gates",
            "",
            "| Gate | Status | Summary |",
            "|---|---|---|",
        ]
    )
    for gate in report.optional_gates:
        lines.append(f"| `{gate.name}` | `{gate.status}` | {gate.summary} |")
    lines.extend(
        [
            "",
            "## Manual Usability Tasks",
            "",
            "| Task | Status | Dependency mode | Observed result | Follow-up |",
            "|---|---|---|---|---|",
        ]
    )
    for task in report.manual_usability_tasks:
        lines.append(
            f"| `{task.task_id}` | `{task.status}` | `{task.dependency_mode}` | "
            f"{task.observed_result} | {task.follow_up_recommendation or '-'} |"
        )
    lines.extend(
        [
            "",
            "Optional gates are reported separately. A skipped optional gate is evidence that the",
            "gate was not requested or its dependency/fixture was unavailable; it is not counted as",
            "a required pass.",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-mode",
        choices=("generated",),
        default="generated",
        help="Fixture source for required live QA gates.",
    )
    parser.add_argument(
        "--real-smoke-policy",
        choices=("auto", "required", "off"),
        default="auto",
        help=(
            "Real smoke policy: auto runs installed real-smoke gates, required fails when "
            "PySide or Demucs is missing, off records skips."
        ),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Optional run directory. Defaults to .build/live_qa_runs/<timestamp>.",
    )
    parser.add_argument(
        "--run-pyside-smoke",
        action="store_true",
        help="Opt in to the optional PySide import smoke.",
    )
    parser.add_argument(
        "--run-demucs-smoke",
        action="store_true",
        help="Opt in to the optional real Demucs source-aware smoke.",
    )
    parser.add_argument(
        "--run-playback-smoke",
        action="store_true",
        help="Opt in to the optional real local playback smoke.",
    )
    parser.add_argument(
        "--playback-smoke-policy",
        choices=("auto", "required", "off"),
        default="auto",
        help=(
            "Playback smoke policy: auto runs only when sounddevice and an output-capable "
            "environment are available, required fails when unavailable, off records a skip."
        ),
    )
    parser.add_argument(
        "--demucs-audio",
        type=Path,
        default=None,
        help="Tiny local audio fixture for the optional real Demucs smoke.",
    )
    parser.add_argument(
        "--demucs-executable",
        type=Path,
        default=None,
        help="Explicit Demucs executable for the optional real source-aware smoke.",
    )
    parser.add_argument(
        "--optional-timeout-sec",
        type=int,
        default=300,
        help="Timeout for requested optional subprocess gates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    args = _parse_args(raw_argv)
    BUILD_DIR.mkdir(exist_ok=True)
    run_dir = args.run_dir or BUILD_DIR / "live_qa_runs" / _safe_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    app_data_dir = run_dir / "app_data"

    required: list[GateResult]
    try:
        required = _run_required_generated(run_dir)
    except Exception as exc:
        required = [
            GateResult(
                name="required_generated_workflow",
                status="failed",
                summary="Required generated live QA workflow failed.",
                details={"error": str(exc)},
            )
        ]

    required_real_smoke = args.real_smoke_policy == "required"
    if args.real_smoke_policy == "off":
        run_pyside_smoke = False
        run_demucs_smoke = False
    elif required_real_smoke:
        run_pyside_smoke = True
        run_demucs_smoke = True
    else:
        run_pyside_smoke = args.run_pyside_smoke or find_spec("PySide6") is not None
        demucs_executable = str(args.demucs_executable or "demucs")
        run_demucs_smoke = args.run_demucs_smoke or shutil.which(demucs_executable) is not None
    optional = [
        _optional_pyside_gate(
            run=run_pyside_smoke,
            required=required_real_smoke,
            run_dir=run_dir,
        ),
        _optional_demucs_gate(
            args,
            run=run_demucs_smoke,
            required=required_real_smoke,
            run_dir=run_dir,
        ),
    ]
    required_playback_smoke = args.playback_smoke_policy == "required"
    if args.playback_smoke_policy == "off":
        run_playback_smoke = False
    elif required_playback_smoke:
        run_playback_smoke = True
    else:
        run_playback_smoke = args.run_playback_smoke or _playback_output_available()
    optional.append(
        _optional_playback_gate(
            run=run_playback_smoke,
            required=required_playback_smoke,
            run_dir=run_dir,
        )
    )
    required_optional_names: set[str] = set()
    if required_real_smoke:
        required_optional_names.update({"pyside_smoke", "real_source_smoke"})
    if required_playback_smoke:
        required_optional_names.add("playback_smoke")
    overall = _report_overall(
        required,
        optional,
        required_optional_names=required_optional_names,
    )
    all_gates = [*required, *optional]
    command = command_metadata(["python3", "scripts/live_qa.py", *raw_argv])
    report = LiveQAReport(
        schema_version=SCHEMA_VERSION,
        command=command,
        environment=runtime_environment(REPO_ROOT),
        dependency_policy=dependency_policy(
            real_smoke_policy=args.real_smoke_policy,
            playback_smoke_policy=args.playback_smoke_policy,
        ),
        inputs={
            "fixture_mode": args.fixture_mode,
            "demucs_audio": None if args.demucs_audio is None else str(args.demucs_audio),
            "demucs_executable": None
            if args.demucs_executable is None
            else str(args.demucs_executable),
        },
        artifacts={
            "json_report": str(JSON_REPORT_PATH),
            "markdown_report": str(MD_REPORT_PATH),
            "run_dir": str(run_dir),
            "app_data_dir": str(app_data_dir),
        },
        timestamp=_utc_timestamp(),
        overall=overall,
        fixture_mode=args.fixture_mode,
        run_dir=str(run_dir),
        app_data_dir=str(app_data_dir),
        required_gates=required,
        optional_gates=optional,
        known_skips=known_skips_from_gates(all_gates),
        follow_up_items=follow_up_items_from_gates(all_gates),
        manual_usability_tasks=_manual_usability_tasks(required, optional, run_dir=run_dir),
    )
    _write_reports(report)

    print(f"live_qa: {overall}")
    print(f"  required: {', '.join(f'{gate.name}={gate.status}' for gate in required)}")
    print(f"  optional: {', '.join(f'{gate.name}={gate.status}' for gate in optional)}")
    print(f"  report: {JSON_REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"  report: {MD_REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
