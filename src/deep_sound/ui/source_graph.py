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
    is_user_corrected: bool = False
    raw_label: str | None = None
    raw_source_type: str | None = None
    correction_id: str | None = None
    parent_id: str | None = None
    search_enabled: bool = False
    compatible_search_modes: tuple[str, ...] = ()


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
                    is_user_corrected=source.is_user_corrected,
                    raw_label=source.raw_label,
                    raw_source_type=(
                        None if source.raw_source_type is None else source.raw_source_type.value
                    ),
                    correction_id=source.correction_id,
                    parent_id=stem.id,
                    search_enabled=source.source_type
                    in {SourceType.PITCHED_HARMONIC, SourceType.MELODIC},
                    compatible_search_modes=_compatible_search_modes(source.source_type),
                )
            )
    return nodes


@dataclass(frozen=True, slots=True)
class SourceDetailData:
    source_id: str
    label: str
    source_type: str
    confidence: float
    is_user_corrected: bool
    raw_label: str | None
    raw_source_type: str | None
    compatible_search_modes: tuple[str, ...]
    correction_id: str | None = None


def source_detail_data(node: SourceGraphNodeData) -> SourceDetailData | None:
    if node.source_type is None:
        return None
    return SourceDetailData(
        source_id=node.node_id,
        label=node.label,
        source_type=node.source_type,
        confidence=node.confidence,
        is_user_corrected=node.is_user_corrected,
        raw_label=node.raw_label,
        raw_source_type=node.raw_source_type,
        compatible_search_modes=node.compatible_search_modes,
        correction_id=node.correction_id,
    )


def _compatible_search_modes(source_type: SourceType) -> tuple[str, ...]:
    if source_type is SourceType.PITCHED_HARMONIC:
        return ("source_chords", "chord_change", "source_role")
    if source_type is SourceType.MELODIC:
        return ("melody", "vocal_timbre", "source_role")
    return ()


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
