from __future__ import annotations

from pathlib import Path

from deep_sound.services.waveform_service import ClipWindowDTO, WaveformCacheDTO, WaveformPointDTO
from deep_sound.ui.waveform_panel import ClipSelectionState, waveform_panel_data


def test_waveform_panel_maps_cache_points_and_clip_state(tmp_path: Path) -> None:
    cache = WaveformCacheDTO(
        track_id="track-1",
        artifact_path=tmp_path / "waveform.json",
        duration_sec=10.0,
        sample_rate=100,
        algorithm="test",
        version="v1",
        points=(
            WaveformPointDTO(
                start_sec=0.0,
                end_sec=5.0,
                min_amplitude=-2.0,
                max_amplitude=2.0,
                rms=0.5,
            ),
        ),
    )
    clip = ClipWindowDTO(id="clip-1", track_id="track-1", start_sec=1.0, end_sec=2.0)

    panel = waveform_panel_data(
        cache,
        selected_clip=ClipSelectionState(
            track_id="track-1",
            start_sec=1.0,
            end_sec=2.0,
            persisted_clip_id="clip-1",
        ),
        persisted_clips=(clip,),
    )

    assert panel.render_points[0].x_end == 0.5
    assert panel.render_points[0].y_min == -1.0
    assert panel.render_points[0].y_max == 1.0
    assert panel.selected_clip is not None
    assert panel.persisted_clips == (clip,)
