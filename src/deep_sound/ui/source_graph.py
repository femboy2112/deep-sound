"""Import-safe source graph UI DTO helpers."""

from __future__ import annotations

from dataclasses import dataclass

from deep_sound.domain.source import SourceType
from deep_sound.services.source_service import SourceGraph


@dataclass(frozen=True, slots=True)
class SourceGraphNodeData:
    node_id: str
    label: str
    confidence: float
    feature_count: int
    disabled_phase3_controls: bool = True
    source_type: str | None = None


def source_graph_nodes(graph: SourceGraph) -> list[SourceGraphNodeData]:
    nodes: list[SourceGraphNodeData] = []
    for graph_stem in graph.stems:
        stem = graph_stem.stem
        nodes.append(
            SourceGraphNodeData(
                node_id=stem.id,
                label=stem.stem_type.value,
                confidence=stem.confidence.value,
                feature_count=len(graph_stem.feature_views),
                source_type=None,
            )
        )
        for source in graph_stem.sources:
            nodes.append(
                SourceGraphNodeData(
                    node_id=source.id,
                    label=source.source_label,
                    confidence=source.confidence.value,
                    feature_count=0,
                    disabled_phase3_controls=source.source_type is not SourceType.PITCHED_HARMONIC,
                    source_type=source.source_type.value,
                )
            )
    return nodes


def create_source_graph_view(graph: SourceGraph) -> object:
    """Create a PySide source graph list from broad-stem DTOs."""
    try:
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)
    for node in source_graph_nodes(graph):
        layout.addWidget(
            QLabel(f"{node.label}  confidence {node.confidence:.0%}  features {node.feature_count}")
        )
    return root
