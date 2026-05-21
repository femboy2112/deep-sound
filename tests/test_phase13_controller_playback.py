from __future__ import annotations

from pathlib import Path

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.index_service import IndexStatus
from deep_sound.services.playback_service import PlaybackRequest, PlaybackService, PlaybackState
from deep_sound.ui.library_workflow import (
    DesktopWorkflowController,
    PlayIntentDTO,
    SeekIntentDTO,
    StopIntentDTO,
)


def test_controller_applies_playback_transport_and_exposes_snapshot_state(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"audio")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=audio_path, duration_sec=4.0))
    transport = PlaybackService()
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        index_service=_FakeIndexService(),
        playback_transport=transport,
    )

    play = controller.play(PlayIntentDTO(track_id="track-1", start_sec=1.0))
    seek = controller.seek(SeekIntentDTO(track_id="track-1", position_sec=99.0))
    stop = controller.stop(StopIntentDTO(track_id="track-1"))
    snapshot = controller.snapshot()

    assert play.state is not None
    assert play.state.status == "playing"
    assert seek.state is not None
    assert seek.state.position_sec == 4.0
    assert stop.action == "stop"
    assert stop.state is not None
    assert stop.state.status == "stopped"
    assert isinstance(snapshot.playback_state, PlaybackState)
    assert snapshot.playback_state.status == "stopped"
    assert snapshot.live_qa is not None
    assert snapshot.live_qa.playback_intents_supported == ("play", "pause", "seek", "stop")


def test_controller_seek_prepares_track_when_transport_is_idle(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.wav"
    audio_path.write_bytes(b"audio")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=audio_path, duration_sec=4.0))
    transport = _RecordingPlaybackService()
    controller = DesktopWorkflowController(
        store,
        app_data_dir=tmp_path / "app_data",
        index_service=_FakeIndexService(),
        playback_transport=transport,
    )

    seek = controller.seek(SeekIntentDTO(track_id="track-1", position_sec=2.0))

    assert seek.state is not None
    assert seek.state.position_sec == 2.0
    assert transport.prepared_track_ids == ["track-1"]


class _RecordingPlaybackService(PlaybackService):
    def __init__(self) -> None:
        super().__init__()
        self.prepared_track_ids: list[str] = []

    def prepare(self, request: PlaybackRequest) -> PlaybackState:
        self.prepared_track_ids.append(request.track.id)
        return super().prepare(request)


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
