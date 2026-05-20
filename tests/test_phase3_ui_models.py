from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.services.source_service import SourceGraph, SourceGraphStem
from deep_sound.ui.query_builder import QueryWeights, phase3_query_control_state
from deep_sound.ui.source_graph import source_graph_nodes


def test_phase3_query_controls_enable_only_for_pitched_harmonic_sources() -> None:
    enabled = phase3_query_control_state(SourceType.PITCHED_HARMONIC)
    disabled = phase3_query_control_state(SourceType.DRUM)

    assert enabled.selected_source_enabled
    assert enabled.chord_change_enabled
    assert enabled.source_chord_enabled
    assert enabled.compatible_source_filter_enabled
    assert not disabled.selected_source_enabled
    assert not disabled.chord_change_enabled


def test_phase3_weights_include_source_chord_modes() -> None:
    weights = QueryWeights(
        rhythm=0.0,
        harmony=0.0,
        timbre=0.0,
        chord_change=1.0,
        source_behavior=1.0,
    ).normalized_phase3_weights()

    assert set(weights) == {
        "rhythm",
        "harmony",
        "timbre",
        "harmony.chord_change",
        "harmony.chord_sequence",
    }
    assert weights["harmony.chord_change"] == 0.2


def test_source_graph_nodes_enable_phase3_controls_for_harmonic_sources() -> None:
    stem = Stem(
        id="track-1:other",
        track_id="track-1",
        stem_type=StemType.OTHER,
        confidence=Confidence(0.8),
        artifact_path=Path("other.wav"),
    )
    source = Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id=stem.id,
        source_type=SourceType.PITCHED_HARMONIC,
        source_label="possible pitched harmonic accompaniment",
        confidence=Confidence(0.7),
    )
    graph = SourceGraph(
        track_id="track-1",
        stems=(SourceGraphStem(stem=stem, sources=(source,), feature_views=()),),
    )

    nodes = source_graph_nodes(graph)

    assert nodes[0].disabled_phase3_controls
    assert not nodes[1].disabled_phase3_controls
    assert nodes[1].source_type == SourceType.PITCHED_HARMONIC.value
