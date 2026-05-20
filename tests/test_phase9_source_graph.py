from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.services.source_service import SourceGraph, SourceGraphStem
from deep_sound.ui.source_graph import source_graph_nodes, source_graph_selection


def test_source_graph_selection_exposes_detail_correction_and_search_actions(
    tmp_path: Path,
) -> None:
    graph = _graph(tmp_path, SourceType.PITCHED_HARMONIC)
    nodes = source_graph_nodes(graph)

    selection = source_graph_selection(nodes, "source-1")

    assert selection.detail is not None
    assert selection.detail.source_id == "source-1"
    assert selection.correction_enabled is True
    assert [action.mode for action in selection.compatible_search_actions] == [
        "source_chords",
        "chord_change",
        "source_role",
    ]
    assert all(action.query_id == "source-1" for action in selection.compatible_search_actions)


def test_source_graph_selection_disables_correction_for_stem(tmp_path: Path) -> None:
    graph = _graph(tmp_path, SourceType.DRUM)
    nodes = source_graph_nodes(graph)

    selection = source_graph_selection(nodes, "stem-1")

    assert selection.detail is None
    assert selection.correction_enabled is False
    assert selection.compatible_search_actions == ()


def test_source_graph_selection_rejects_missing_node(tmp_path: Path) -> None:
    graph = _graph(tmp_path, SourceType.MELODIC)

    with pytest.raises(KeyError, match="missing"):
        source_graph_selection(source_graph_nodes(graph), "missing")


def _graph(tmp_path: Path, source_type: SourceType) -> SourceGraph:
    stem = Stem(
        id="stem-1",
        track_id="track-1",
        stem_type=StemType.OTHER,
        confidence=Confidence(0.8),
        artifact_path=tmp_path / "stem.wav",
    )
    source = Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id=stem.id,
        source_type=source_type,
        source_label="possible source",
        confidence=Confidence(0.7),
    )
    return SourceGraph(
        track_id="track-1",
        stems=(SourceGraphStem(stem=stem, sources=(source,), feature_views=()),),
    )
