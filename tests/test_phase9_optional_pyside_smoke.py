from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.track import Track
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.main_window import create_main_window
from deep_sound.ui.track_detail import create_track_detail_widget


def test_phase9_optional_pyside_main_window_widgets_open_with_fake_controller(
    tmp_path: Path,
) -> None:
    pytest.importorskip("PySide6")

    track = Track(
        id="track-1",
        filepath=tmp_path / "song.wav",
        title="Song",
        duration_sec=1.0,
    )
    controller = _FakeController()

    window = create_main_window(
        (track,),
        controller=controller,
        active_profile=AnalysisProfile.SEARCHABLE,
    )
    detail = create_track_detail_widget(track)

    assert window is not None
    assert detail is not None


class _FakeController:
    def import_paths(self, intent: object) -> object:
        return intent

    def analyze(self, intent: object) -> object:
        return intent

    def build_index(self, intent: object) -> object:
        return intent

    def search(self, intent: object) -> object:
        return intent

    def snapshot(self) -> object:
        return object()
