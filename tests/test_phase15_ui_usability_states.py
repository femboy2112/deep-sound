from __future__ import annotations

from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.main_window import MainWindowActionBinder, main_window_usability_state


class _Controller:
    def __init__(self) -> None:
        self.play_count = 0
        self.search_count = 0

    def search(self, intent: object) -> str:
        self.search_count += 1
        return "searched"

    def play(self, intent: object) -> str:
        self.play_count += 1
        return "played"


def test_main_window_usability_state_disables_invalid_actions() -> None:
    state = main_window_usability_state(track_count=0, playback_error="No output device")

    actions = {action.action_id: action for action in state.actions}
    assert state.library_empty_state == "No tracks imported."
    assert state.result_empty_state == "No search results."
    assert actions["analyze_library"].enabled is False
    assert actions["search_selected"].enabled is False
    assert actions["play_selected"].reason == "Select a track before playback."
    assert state.playback_status_text == "Playback failed: No output device"
    assert "Playback unavailable: No output device" in state.error_states


def test_main_window_usability_state_surfaces_stale_and_failed_states() -> None:
    state = main_window_usability_state(
        track_count=2,
        job_count=1,
        result_count=3,
        selected_track_id="track-1",
        selected_result_id="result-1",
        failed_job_count=1,
        stale_index_warning_count=1,
    )

    actions = {action.action_id: action for action in state.actions}
    assert state.library_empty_state == ""
    assert state.queue_empty_state == ""
    assert actions["build_index"].enabled is True
    assert actions["search_selected"].enabled is True
    assert actions["result_feedback"].enabled is True
    assert any("failed job" in error for error in state.error_states)
    assert any("stale" in error for error in state.error_states)


def test_binder_blocks_selected_track_actions_until_selection() -> None:
    controller = _Controller()
    binder = MainWindowActionBinder(
        controller=controller,  # type: ignore[arg-type]
        active_profile=AnalysisProfile.SEARCHABLE,
    )

    assert binder.can_use_selected_track_actions is False
    assert binder.search_selected() is None
    assert binder.play_selected() is None

    binder.set_selected_track("track-1")

    assert binder.can_use_selected_track_actions is True
    assert binder.search_selected() == "searched"
    assert binder.play_selected() == "played"
    assert controller.search_count == 1
    assert controller.play_count == 1
