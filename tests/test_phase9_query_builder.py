from __future__ import annotations

from deep_sound.domain.feature_view import OwnerType
from deep_sound.domain.source import SourceType
from deep_sound.services.similarity_service import SearchMode
from deep_sound.ui.query_builder import QueryWeights, interactive_query_builder_state


def test_interactive_query_builder_builds_search_intent_for_clip() -> None:
    state = interactive_query_builder_state(
        selected_query_id="clip-1",
        selected_owner_type=OwnerType.CLIP,
        selected_search_mode=SearchMode.WEIGHTED,
        weights=QueryWeights(rhythm=1.0, harmony=0.0, timbre=0.0),
        clip_start_sec=1.0,
        clip_end_sec=2.0,
    )

    assert state.can_search is True
    assert state.desktop_query.search_intent is not None
    assert state.desktop_query.search_intent.query_id == "clip-1"
    assert state.desktop_query.search_intent.mode == "weighted"
    assert state.desktop_query.weights["rhythm"] == 1.0
    assert state.validation_messages == ()


def test_interactive_query_builder_blocks_missing_query_and_bad_clip_window() -> None:
    state = interactive_query_builder_state(
        selected_query_id=None,
        selected_owner_type=OwnerType.CLIP,
        selected_search_mode=SearchMode.RHYTHM,
        clip_start_sec=2.0,
        clip_end_sec=1.0,
    )

    assert state.can_search is False
    assert state.desktop_query.search_intent is None
    assert state.validation_messages == (
        "Select a track, clip, or source before searching.",
        "Clip query end must be after start.",
    )


def test_interactive_query_builder_blocks_incompatible_source_mode() -> None:
    state = interactive_query_builder_state(
        selected_query_id="source-1",
        selected_owner_type=OwnerType.SOURCE,
        selected_search_mode=SearchMode.SOURCE_CHORDS,
        source_type=SourceType.DRUM,
    )

    assert state.can_search is False
    assert state.desktop_query.search_intent is None
    assert state.validation_messages == (
        "Selected source type is not compatible with this search mode.",
    )
