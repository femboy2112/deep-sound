from __future__ import annotations

import importlib
import sys
from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import JobRecord, SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisSummary
from deep_sound.services.waveform_service import WaveformPointDTO
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    DesktopWorkflowController,
    ImportIntentDTO,
    IndexIntentDTO,
    WaveformCacheDTO,
    WaveformIntentDTO,
    WorkflowJobDTO,
    job_dto,
)


def test_job_dto_derives_progress_stage_and_retry_actions(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    running_index = store.create_job(
        job_type="desktop_index_searchable",
        target_type="library",
        target_id="library",
        status="running",
        progress=0.60,
    )
    failed_waveform = store.create_job(
        job_type="desktop_waveform",
        target_type="track",
        target_id="track-1",
        status="failed",
        progress=0.20,
        error_message="decode failed",
    )
    legacy_analysis = store.create_job(
        job_type="analyze_searchable",
        target_type="track",
        target_id="track-2",
        status="failed",
        progress=1.0,
        error_message="feature failed",
    )

    index_dto = job_dto(running_index)
    waveform_dto = job_dto(failed_waveform)
    legacy_dto = job_dto(legacy_analysis)

    assert index_dto.stage == "indexing"
    assert index_dto.stage_label == "Building indexes"
    assert index_dto.progress_label == "60%"
    assert waveform_dto.stage == "failed"
    assert waveform_dto.retry_enabled is True
    assert waveform_dto.retry_action is not None
    assert waveform_dto.retry_action.controller_method == "retry_build_waveform"
    assert waveform_dto.retry_action.intent_type == "WaveformIntentDTO"
    assert legacy_dto.retry_action is not None
    assert legacy_dto.retry_action.controller_method == "retry_analyze"


def test_controller_reports_import_analyze_index_and_waveform_stages(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    observed: list[WorkflowJobDTO] = []
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        library_service=_ProgressLibrary(store, observed),
        analysis_service=_ProgressAnalysis(store, observed),
        index_service=_ProgressIndex(store, observed),
        waveform_service=_ProgressWaveforms(store, observed),
    )

    import_job = controller.import_paths(ImportIntentDTO(paths=(tmp_path / "song.wav",)))
    track = store.list_tracks()[0]
    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    waveform_job, cache = controller.build_waveform(WaveformIntentDTO(track_id=track.id))

    assert [job.stage for job in observed] == [
        "importing",
        "analyzing",
        "indexing",
        "loading",
    ]
    assert import_job.stage == "completed"
    assert analyze_job.stage == "completed"
    assert index_job.stage == "completed"
    assert waveform_job.stage == "completed"
    assert cache.track_id == track.id


def test_library_workflow_import_does_not_load_pyside() -> None:
    for module_name in tuple(sys.modules):
        if module_name == "PySide6" or module_name.startswith("PySide6."):
            del sys.modules[module_name]

    importlib.import_module("deep_sound.ui.library_workflow")

    assert "PySide6" not in sys.modules
    assert not any(module_name.startswith("PySide6.") for module_name in sys.modules)


class _ProgressLibrary:
    def __init__(self, store: SqliteStore, observed: list[WorkflowJobDTO]) -> None:
        self._store = store
        self._observed = observed

    def import_file(self, path: Path) -> Track:
        self._observed.append(job_dto(_running_job(self._store)))
        return self._store.add_track(
            Track(
                id="track-1",
                filepath=path,
                title="Song",
                audio_hash="hash-1",
            )
        )

    def import_folder(self, path: Path, recursive: bool = True) -> list[Track]:
        return [self.import_file(path / "song.wav")]


class _ProgressAnalysis:
    def __init__(self, store: SqliteStore, observed: list[WorkflowJobDTO]) -> None:
        self._store = store
        self._observed = observed

    def analyze_library(
        self,
        tracks: object = None,
        *,
        profile: AnalysisProfile | str = AnalysisProfile.MINIMAL,
    ) -> LibraryAnalysisSummary:
        self._observed.append(job_dto(_running_job(self._store)))
        selected = AnalysisProfile(profile)
        return LibraryAnalysisSummary(
            profile=selected,
            requested_count=1,
            completed_count=1,
            failed_count=0,
            feature_count=3,
            results=(),
        )


class _ProgressIndex:
    def __init__(self, store: SqliteStore, observed: list[WorkflowJobDTO]) -> None:
        self._store = store
        self._observed = observed

    def build_profile(self, profile: AnalysisProfile | str) -> tuple[IndexStatus, ...]:
        self._observed.append(job_dto(_running_job(self._store)))
        return (self.status(FeatureType.RHYTHM_GLOBAL),)

    def status(
        self,
        feature_type: FeatureType,
        *,
        owner_type: OwnerType = OwnerType.TRACK,
        record: object = None,
    ) -> IndexStatus:
        return IndexStatus(
            feature_type=feature_type,
            owner_type=owner_type,
            available=True,
            stale=False,
            backend="numpy",
            feature_count=1,
            dim=1,
        )


class _ProgressWaveforms:
    def __init__(self, store: SqliteStore, observed: list[WorkflowJobDTO]) -> None:
        self._store = store
        self._observed = observed

    def build_cache(self, track: Track, *, point_count: int = 512) -> WaveformCacheDTO:
        self._observed.append(job_dto(_running_job(self._store)))
        return WaveformCacheDTO(
            track_id=track.id,
            artifact_path=Path("waveforms") / f"{track.id}.json",
            duration_sec=1.0,
            sample_rate=44_100,
            algorithm="fake_waveform",
            version="test",
            points=(
                WaveformPointDTO(
                    start_sec=0.0,
                    end_sec=1.0,
                    min_amplitude=0.0,
                    max_amplitude=0.0,
                    rms=0.0,
                ),
            ),
        )


def _running_job(store: SqliteStore) -> JobRecord:
    for job in reversed(store.list_jobs()):
        if job.status == "running":
            return job
    raise AssertionError("expected a running workflow job")
