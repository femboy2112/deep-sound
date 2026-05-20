from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisSummary
from deep_sound.services.similarity_service import SimilarityResult
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


def test_desktop_controller_import_waveform_clip_feedback_and_snapshot(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        analysis_service=_FakeAnalysisService(),
        index_service=_FakeIndexService(),
        similarity_service=_FakeSimilarityService(),
    )

    import_job = controller.import_paths(ImportIntentDTO(paths=(click_track_wav,)))
    track = store.list_tracks()[0]
    analyze_job = controller.analyze(AnalyzeIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    index_job = controller.build_index(IndexIntentDTO(profile=AnalysisProfile.SEARCHABLE))
    waveform_job, cache = controller.build_waveform(WaveformIntentDTO(track_id=track.id))
    clip, query = controller.create_clip_selection(
        ClipSelectionIntentDTO(track_id=track.id, start_sec=0.1, end_sec=0.5, label="hook")
    )
    results = controller.search(SearchIntentDTO(query_id=track.id, mode="rhythm"))
    feedback_job = controller.submit_feedback(
        FeedbackIntentDTO(
            query_owner_id=track.id,
            result_owner_id="candidate",
            value="relevant",
        )
    )
    snapshot = controller.snapshot()

    assert import_job.status == "completed"
    assert analyze_job.status == "completed"
    assert index_job.status == "completed"
    assert waveform_job.status == "completed"
    assert cache.track_id == track.id
    assert clip.id == query.query_owner_id
    assert query.query_owner_type is OwnerType.CLIP
    assert results[0].query_owner_id == track.id
    assert results[0].result_owner_id == "candidate"
    assert feedback_job.status == "completed"
    assert snapshot.track_count == 1
    assert snapshot.clip_count == 1


def test_desktop_controller_maps_job_failure(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    controller = DesktopWorkflowController(store, app_data_dir=tmp_path / "app_data")

    job = controller.import_paths(ImportIntentDTO(paths=(tmp_path / "missing.wav",)))

    assert job.status == "failed"
    assert job.retry_enabled is True
    assert job.error_message is not None


class _FakeAnalysisService:
    def analyze_library(
        self,
        tracks: object = None,
        *,
        profile: AnalysisProfile | str = AnalysisProfile.MINIMAL,
    ) -> LibraryAnalysisSummary:
        selected = AnalysisProfile(profile)
        return LibraryAnalysisSummary(
            profile=selected,
            requested_count=1,
            completed_count=1,
            failed_count=0,
            feature_count=3,
            results=(),
        )


class _FakeIndexService:
    def build_profile(self, profile: AnalysisProfile | str) -> tuple[IndexStatus, ...]:
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


class _FakeSimilarityService:
    def search(
        self,
        query_id: str,
        weights: dict[str, float],
        top_k: int = 10,
        owner_type: OwnerType | None = None,
    ) -> list[SimilarityResult]:
        return [
            SimilarityResult(
                owner_id="candidate",
                score=0.9,
                dimension_scores={"rhythm.global": 0.9},
                owner_type=OwnerType.TRACK,
                matched_entity_type="track",
                search_backend="index",
            )
        ]
