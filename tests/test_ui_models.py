"""Import-safe tests for Phase 1 UI DTO helpers."""

from __future__ import annotations

from pathlib import Path

from deep_sound.domain.track import Track
from deep_sound.ui.main_window import library_rows
from deep_sound.ui.query_builder import QueryWeights
from deep_sound.ui.results_view import confidence_warnings


def test_library_rows_format_track_metadata_without_pyside() -> None:
    rows = library_rows(
        [
            Track(
                id="track-1",
                filepath=Path("song.wav"),
                title=None,
                artist=None,
                duration_sec=125.2,
                analysis_status="pending",
            )
        ]
    )

    assert rows[0].title == "song"
    assert rows[0].artist == "Unknown artist"
    assert rows[0].duration == "2:05"
    assert rows[0].analysis_status == "pending"


def test_query_weights_normalize_phase1_dimensions_only() -> None:
    weights = QueryWeights(rhythm=1.0, harmony=1.0, chord_change=5.0, timbre=2.0)

    assert weights.normalized_phase1_weights() == {"rhythm": 0.25, "harmony": 0.25, "timbre": 0.5}


def test_result_warnings_flag_low_confidence_dimensions() -> None:
    warnings = confidence_warnings({"rhythm": 0.8, "harmony": 0.42})

    assert warnings == ("harmony is low-confidence (0.42)",)
