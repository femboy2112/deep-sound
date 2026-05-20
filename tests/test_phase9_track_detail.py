from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track
from deep_sound.services.waveform_service import ClipWindowDTO, WaveformCacheDTO, WaveformPointDTO
from deep_sound.ui.track_detail import track_detail_data
from deep_sound.ui.waveform_panel import ClipSelectionState


def test_track_detail_data_includes_selected_track_waveform_and_clip(
    tmp_path: Path,
) -> None:
    track = Track(
        id="track-1",
        filepath=tmp_path / "song.wav",
        title="Song",
        duration_sec=12.4,
        analysis_status="analyzed",
    )
    cache = WaveformCacheDTO(
        track_id="track-1",
        artifact_path=tmp_path / "waveform.json",
        duration_sec=12.4,
        sample_rate=100,
        algorithm="test",
        version="v1",
        points=(
            WaveformPointDTO(
                start_sec=0.0,
                end_sec=6.2,
                min_amplitude=-0.25,
                max_amplitude=0.5,
                rms=0.2,
            ),
        ),
    )
    selected = ClipSelectionState(
        track_id="track-1",
        start_sec=1.0,
        end_sec=2.5,
        label="hook",
    )
    persisted = ClipWindowDTO(
        id="clip-1",
        track_id="track-1",
        start_sec=1.0,
        end_sec=2.5,
        label="hook",
    )

    detail = track_detail_data(
        track,
        waveform_cache=cache,
        selected_clip=selected,
        persisted_clips=(persisted,),
    )

    assert detail.track_id == "track-1"
    assert detail.title == "Song"
    assert detail.analysis_status == "analyzed"
    assert detail.duration == "0:12"
    assert detail.selected_clip == selected
    assert detail.waveform is not None
    assert detail.waveform.track_id == "track-1"
    assert detail.waveform.selected_clip == selected
    assert detail.waveform.persisted_clips == (persisted,)


def test_track_detail_data_handles_missing_waveform(tmp_path: Path) -> None:
    track = Track(id="track-1", filepath=tmp_path / "song.wav")

    detail = track_detail_data(track)

    assert detail.title == "song"
    assert detail.duration == "-"
    assert detail.waveform is None
