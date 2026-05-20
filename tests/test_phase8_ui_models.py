from __future__ import annotations

from deep_sound.domain.feature_view import OwnerType
from deep_sound.domain.source import SourceType
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SearchMode
from deep_sound.ui.main_window import main_window_action_map
from deep_sound.ui.query_builder import QueryWeights, desktop_query_state


def test_main_window_action_map_builds_workflow_intents() -> None:
    actions = main_window_action_map(
        active_profile=AnalysisProfile.SEARCHABLE,
        selected_track_id="track-1",
    )

    assert actions.analyze_intent.profile is AnalysisProfile.SEARCHABLE
    assert actions.index_intent.profile is AnalysisProfile.SEARCHABLE
    assert actions.refresh_action == "refresh_library_state"
    assert actions.selected_track_search is not None
    assert actions.selected_track_search.query_id == "track-1"


def test_desktop_query_state_maps_clip_and_weighted_modes() -> None:
    state = desktop_query_state(
        query_owner_id="clip-1",
        query_owner_type=OwnerType.CLIP,
        search_mode=SearchMode.WEIGHTED,
        weights=QueryWeights(rhythm=1.0, harmony=0.0, timbre=0.0),
        clip_start_sec=1.0,
        clip_end_sec=2.0,
    )

    assert state.query_owner_type is OwnerType.CLIP
    assert state.weights["rhythm"] == 1.0
    assert state.warnings == ()


def test_desktop_query_state_warns_for_incompatible_source_mode() -> None:
    state = desktop_query_state(
        query_owner_id="source-1",
        query_owner_type=OwnerType.SOURCE,
        search_mode=SearchMode.SOURCE_CHORDS,
        source_type=SourceType.DRUM,
    )

    assert state.warnings == ("Selected source type is not compatible with this search mode.",)
