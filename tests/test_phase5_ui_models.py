from __future__ import annotations

from deep_sound.domain.source import SourceType
from deep_sound.ui.query_builder import QueryWeights, phase5_query_control_state
from deep_sound.ui.results_view import ResultCardData


def test_query_weights_normalize_phase5_without_changing_phase1() -> None:
    weights = QueryWeights(
        rhythm=1.0,
        harmony=0.0,
        timbre=1.0,
        production=2.0,
        structure=2.0,
    )

    assert weights.normalized_phase1_weights() == {
        "rhythm": 0.5,
        "harmony": 0.0,
        "timbre": 0.5,
    }
    phase5 = weights.normalized_phase5_weights()
    assert phase5["production.texture"] == phase5["structure.section_sequence"]
    assert sum(phase5.values()) == 1.0


def test_phase5_query_controls_gate_source_dimensions() -> None:
    drum_state = phase5_query_control_state(SourceType.DRUM)
    melodic_state = phase5_query_control_state(SourceType.MELODIC)

    assert drum_state.production_enabled
    assert not drum_state.melody_enabled
    assert melodic_state.melody_enabled
    assert melodic_state.source_role_enabled


def test_result_card_data_carries_phase5_metadata() -> None:
    card = ResultCardData(
        track_title="Song",
        artist=None,
        combined_score=0.8,
        dimension_scores={"production.texture": 0.8},
        explanation="Possible match.",
        matched_entity_type="track",
        caveats=("Production texture evidence is probabilistic.",),
    )

    assert card.matched_entity_type == "track"
    assert card.caveats == ("Production texture evidence is probabilistic.",)
