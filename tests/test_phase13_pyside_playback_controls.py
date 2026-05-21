from __future__ import annotations

import sys
from pathlib import Path

import pytest

from deep_sound.domain.track import Track
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.playback_service import PlaybackState, PlaybackStatus
from deep_sound.ui.main_window import MainWindowActionBinder, create_main_window
from deep_sound.ui.track_detail import create_track_detail_widget


def test_main_window_binder_routes_selected_playback_actions() -> None:
    controller = _FakeController()
    binder = MainWindowActionBinder(
        controller=controller,
        active_profile=AnalysisProfile.SEARCHABLE,
    )

    assert binder.play_selected() is None
    binder.set_selected_track("track-1")

    assert binder.play_selected(start_sec=1.5) == "played"
    assert binder.pause_selected(position_sec=1.75) == "paused"
    assert binder.seek_selected(2.0) == "seeked"
    assert binder.stop_selected() == "stopped"

    assert [intent.track_id for intent in controller.playbacks] == ["track-1"] * 4


def test_pyside_track_detail_playback_buttons_call_callbacks(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QPushButton  # type: ignore[import-not-found]

    app = QApplication.instance() or QApplication(sys.argv[:1])
    track = Track(id="track-1", filepath=tmp_path / "song.wav", duration_sec=3.0)
    state = PlaybackState(
        track_id="track-1",
        source_path=track.filepath,
        status=PlaybackStatus.PAUSED,
        position_sec=1.0,
        duration_sec=3.0,
        backend="local-sounddevice",
    )
    actions: list[str] = []
    detail = create_track_detail_widget(
        track,
        playback_state=state,
        on_play=lambda action: actions.append(action.action.value),
        on_pause=lambda action: actions.append(action.action.value),
        on_seek=lambda action: actions.append(action.action.value),
        on_stop=lambda action: actions.append(action.action.value),
    )

    for button in detail.findChildren(QPushButton):
        if button.text() in {"Play", "Pause", "Seek", "Stop"}:
            button.click()

    assert app is not None
    assert actions == ["play", "pause", "seek", "stop"]


def test_pyside_main_window_exposes_selected_playback_buttons(tmp_path: Path) -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QPushButton  # type: ignore[import-not-found]

    app = QApplication.instance() or QApplication(sys.argv[:1])
    track = Track(id="track-1", filepath=tmp_path / "song.wav", title="Song")
    window = create_main_window(
        (track,),
        controller=_FakeController(),
        active_profile=AnalysisProfile.SEARCHABLE,
    )
    labels = {button.text() for button in window.findChildren(QPushButton)}

    assert app is not None
    assert {"Play", "Pause", "Stop"}.issubset(labels)


class _FakeController:
    def __init__(self) -> None:
        self.playbacks: list[object] = []

    def import_paths(self, intent: object) -> object:
        return intent

    def analyze(self, intent: object) -> object:
        return intent

    def build_index(self, intent: object) -> object:
        return intent

    def search(self, intent: object) -> tuple[object, ...]:
        return ()

    def play(self, intent: object) -> str:
        self.playbacks.append(intent)
        return "played"

    def pause(self, intent: object) -> str:
        self.playbacks.append(intent)
        return "paused"

    def seek(self, intent: object) -> str:
        self.playbacks.append(intent)
        return "seeked"

    def stop(self, intent: object) -> str:
        self.playbacks.append(intent)
        return "stopped"

    def snapshot(self) -> object:
        return object()
