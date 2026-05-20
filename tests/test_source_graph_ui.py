from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.services.source_service import SourceGraph, SourceGraphStem
from deep_sound.ui.source_graph import source_graph_nodes


def test_source_graph_nodes_expose_broad_stems_without_pyside() -> None:
    stem = Stem(
        id="track-1:drums",
        track_id="track-1",
        stem_type=StemType.DRUMS,
        confidence=Confidence(0.7),
        artifact_path=Path("drums.wav"),
    )
    source = Source(
        id="track-1:drums:source",
        track_id="track-1",
        parent_stem_id=stem.id,
        source_type=SourceType.DRUM,
        source_label="possible drums stem",
        confidence=Confidence(0.7),
    )
    graph = SourceGraph(
        track_id="track-1",
        stems=(SourceGraphStem(stem=stem, sources=(source,), feature_views=()),),
    )

    nodes = source_graph_nodes(graph)

    assert [node.label for node in nodes] == ["drums", "possible drums stem"]
    assert all(node.disabled_phase3_controls for node in nodes)
    assert all(0.0 <= node.confidence <= 1.0 for node in nodes)
