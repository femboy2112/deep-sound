from __future__ import annotations

import json
from pathlib import Path

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.track import Track
from deep_sound.services.waveform_service import WaveformService, clip_window_dto


def test_waveform_service_writes_cache_artifact_without_pyside(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    track = Track(
        id="track-1",
        filepath=click_track_wav,
        title="Song",
        audio_hash="hash",
    )

    dto = WaveformService(tmp_path / "app_data").build_cache(track, point_count=32)

    assert dto.track_id == track.id
    assert dto.artifact_path.exists()
    assert dto.sample_rate > 0
    assert dto.duration_sec > 0.0
    assert len(dto.points) <= 32
    payload = json.loads(dto.artifact_path.read_text())
    assert payload["track_id"] == track.id
    assert payload["version"] == dto.version
    assert payload["points"]


def test_clip_window_dto_is_import_safe() -> None:
    clip = ClipWindow(
        id="clip-1",
        track_id="track-1",
        start_sec=1.0,
        end_sec=3.0,
        label="hook",
    )

    dto = clip_window_dto(clip)

    assert dto.id == clip.id
    assert dto.start_sec == 1.0
    assert dto.end_sec == 3.0
    assert dto.label == "hook"
