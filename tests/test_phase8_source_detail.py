from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.services.source_service import SourceGraph, SourceGraphStem
from deep_sound.ui.source_graph import source_detail_data, source_graph_nodes


def test_source_detail_exposes_correction_and_compatible_controls(tmp_path: Path) -> None:
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
        source_type=SourceType.PITCHED_HARMONIC,
        source_label="corrected guitar-like source",
        confidence=Confidence(0.7),
        is_user_corrected=True,
        raw_label="possible accompaniment stem",
        raw_source_type=SourceType.UNKNOWN,
        correction_id="correction-1",
    )
    graph = SourceGraph(
        track_id="track-1",
        stems=(SourceGraphStem(stem=stem, sources=(source,), feature_views=()),),
    )

    source_node = source_graph_nodes(graph)[1]
    detail = source_detail_data(source_node)

    assert detail is not None
    assert detail.raw_label == "possible accompaniment stem"
    assert detail.raw_source_type == SourceType.UNKNOWN.value
    assert detail.correction_id == "correction-1"
    assert "source_chords" in detail.compatible_search_modes
