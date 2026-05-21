"""Run non-mutating live beta QA and write structured evidence reports."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import numpy as np
    import soundfile as sf
except ModuleNotFoundError:
    if __name__ != "__main__" or os.environ.get("DEEP_SOUND_LIVE_QA_REEXEC") == "1":
        raise
    env = os.environ.copy()
    env["DEEP_SOUND_LIVE_QA_REEXEC"] = "1"
    os.execvpe("uv", ["uv", "run", "python3", str(Path(__file__).resolve()), *sys.argv[1:]], env)

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
class LiveQAReport:
    timestamp: str
    overall: str
    fixture_mode: str
    run_dir: str
    app_data_dir: str
    required_gates: list[GateResult]
    optional_gates: list[GateResult]


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


def _optional_pyside_gate(*, run: bool, run_dir: Path) -> GateResult:
    if not run:
        return GateResult(
            name="pyside_smoke",
            status="skipped_optional",
            optional=True,
            summary="PySide smoke was not requested.",
        )
    if find_spec("PySide6") is None:
        return GateResult(
            name="pyside_smoke",
            status="skipped_optional",
            optional=True,
            summary="PySide smoke was requested but PySide6 is not installed.",
        )
    try:
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


def _optional_demucs_gate(args: argparse.Namespace, run_dir: Path) -> GateResult:
    if not args.run_demucs_smoke:
        return GateResult(
            name="real_source_smoke",
            status="skipped_optional",
            optional=True,
            summary="Real Demucs source-aware smoke was not requested.",
        )
    if args.demucs_audio is None:
        return GateResult(
            name="real_source_smoke",
            status="skipped_optional",
            optional=True,
            summary="Real Demucs source-aware smoke was requested without --demucs-audio.",
        )
    audio_path = args.demucs_audio.expanduser()
    if not audio_path.is_file():
        return GateResult(
            name="real_source_smoke",
            status="skipped_optional",
            optional=True,
            summary=f"Real Demucs source-aware smoke fixture is not a file: {audio_path}",
        )

    env = os.environ.copy()
    env["DEEP_SOUND_RUN_DEMUCS_SMOKE"] = "1"
    env["DEEP_SOUND_DEMUCS_SMOKE_AUDIO"] = str(audio_path)
    if args.demucs_executable is not None:
        env["DEEP_SOUND_DEMUCS_EXECUTABLE"] = str(args.demucs_executable)
    argv = [
        "uv",
        "run",
        "pytest",
        "tests/test_phase10_optional_demucs_smoke.py",
        "-q",
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


def _report_overall(required: list[GateResult], optional: list[GateResult]) -> str:
    failures = [gate for gate in (*required, *optional) if gate.status == "failed"]
    return "fail" if failures else "pass"


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
    args = _parse_args(sys.argv[1:] if argv is None else argv)
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

    optional = [
        _optional_pyside_gate(run=args.run_pyside_smoke, run_dir=run_dir),
        _optional_demucs_gate(args, run_dir),
    ]
    overall = _report_overall(required, optional)
    report = LiveQAReport(
        timestamp=_utc_timestamp(),
        overall=overall,
        fixture_mode=args.fixture_mode,
        run_dir=str(run_dir),
        app_data_dir=str(app_data_dir),
        required_gates=required,
        optional_gates=optional,
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
