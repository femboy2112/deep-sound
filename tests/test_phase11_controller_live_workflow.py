from __future__ import annotations

from pathlib import Path

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import (
    DesktopWorkflowController,
    PauseIntentDTO,
    PlayIntentDTO,
    SeekIntentDTO,
)


def test_controller_playback_intents_resolve_track_metadata_and_positions(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"audio")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(
        Track(
            id="track-1",
            filepath=audio_path,
            title="Song",
            duration_sec=12.5,
        )
    )
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        index_service=_FakeIndexService(),
    )

    play = controller.play(PlayIntentDTO(track_id="track-1", start_sec=-2.0))
    seek = controller.seek(SeekIntentDTO(track_id="track-1", position_sec=20.0))
    pause = controller.pause(PauseIntentDTO(track_id="track-1", position_sec=3.25))

    assert play.action == "play"
    assert play.track_id == "track-1"
    assert play.filepath == audio_path
    assert play.position_sec == 0.0
    assert play.duration_sec == 12.5
    assert play.request_id
    assert seek.action == "seek"
    assert seek.position_sec == 12.5
    assert pause.action == "pause"
    assert pause.position_sec == 3.25


def test_controller_snapshot_includes_live_qa_metadata(
    tmp_path: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav"))
    store.add_clip_window(
        ClipWindow(
            id="clip-1",
            track_id="track-1",
            start_sec=0.5,
            end_sec=1.5,
            label="hook",
        )
    )
    store.create_job(
        job_type="desktop_import",
        target_type="library",
        target_id="library",
        status="failed",
        progress=0.25,
        error_message="fixture import failed",
    )
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        active_profile=AnalysisProfile.SEARCHABLE,
        index_service=_FakeIndexService(),
    )

    snapshot = controller.snapshot()

    assert snapshot.live_qa is not None
    assert snapshot.live_qa.track_count == 1
    assert snapshot.live_qa.clip_count == 1
    assert snapshot.live_qa.job_count == 1
    assert snapshot.live_qa.failed_job_count == 1
    assert snapshot.live_qa.warning_count == 0
    assert snapshot.live_qa.index_status_count == len(snapshot.index_statuses)
    assert snapshot.live_qa.playback_intents_supported == ("play", "pause", "seek")
    assert snapshot.live_qa.active_profile == "searchable"


class _FakeIndexService:
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
