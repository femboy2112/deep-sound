"""Weighted query builder controls for Phase 1 similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.source import SourceType
from deep_sound.services.similarity_service import SearchMode

if TYPE_CHECKING:
    from deep_sound.ui.library_workflow import SearchIntentDTO


@dataclass(frozen=True, slots=True)
class QueryWeights:
    rhythm: float = 0.25
    harmony: float = 0.25
    chord_change: float = 0.0
    source_behavior: float = 0.0
    timbre: float = 0.50
    production: float = 0.0
    structure: float = 0.0
    melody: float = 0.0
    vocal_timbre: float = 0.0
    source_role: float = 0.0

    def normalized_phase1_weights(self) -> dict[str, float]:
        weights = {
            "rhythm": max(0.0, self.rhythm),
            "harmony": max(0.0, self.harmony),
            "timbre": max(0.0, self.timbre),
        }
        total = sum(weights.values())
        if total <= 0.0:
            return {"rhythm": 1.0, "harmony": 1.0, "timbre": 1.0}
        return {key: value / total for key, value in weights.items()}

    def normalized_phase3_weights(self) -> dict[str, float]:
        weights = self.normalized_phase1_weights()
        chord_change = max(0.0, self.chord_change)
        source_behavior = max(0.0, self.source_behavior)
        if chord_change > 0.0:
            weights["harmony.chord_change"] = chord_change
        if source_behavior > 0.0:
            weights["harmony.chord_sequence"] = source_behavior
        total = sum(weights.values())
        return {key: value / total for key, value in weights.items()}

    def normalized_phase5_weights(self) -> dict[str, float]:
        weights = self.normalized_phase3_weights()
        phase5 = {
            "production.texture": max(0.0, self.production),
            "structure.section_sequence": max(0.0, self.structure),
            "melody.contour": max(0.0, self.melody),
            "timbre.embedding": max(0.0, self.vocal_timbre),
            "source_role": max(0.0, self.source_role),
        }
        weights.update({key: value for key, value in phase5.items() if value > 0.0})
        total = sum(weights.values())
        if total <= 0.0:
            return {"production.texture": 1.0}
        return {key: value / total for key, value in weights.items()}


@dataclass(frozen=True, slots=True)
class Phase5QueryControlState:
    production_enabled: bool = True
    structure_enabled: bool = True
    melody_enabled: bool = False
    vocal_timbre_enabled: bool = False
    source_role_enabled: bool = False


@dataclass(frozen=True, slots=True)
class DesktopQueryState:
    query_owner_id: str
    query_owner_type: OwnerType
    search_mode: SearchMode
    weights: dict[str, float]
    source_type: SourceType | None = None
    clip_start_sec: float | None = None
    clip_end_sec: float | None = None
    warnings: tuple[str, ...] = ()
    search_enabled: bool = True
    search_intent: SearchIntentDTO | None = None


def desktop_query_state(
    *,
    query_owner_id: str,
    query_owner_type: OwnerType,
    search_mode: SearchMode | str,
    weights: QueryWeights | None = None,
    source_type: SourceType | None = None,
    clip_start_sec: float | None = None,
    clip_end_sec: float | None = None,
) -> DesktopQueryState:
    mode = SearchMode(search_mode)
    current_weights = weights or QueryWeights()
    warnings: list[str] = []
    search_enabled = True
    if not query_owner_id:
        warnings.append("Select a track, clip, or source before searching.")
        search_enabled = False
    if query_owner_type is OwnerType.CLIP and (clip_start_sec is None or clip_end_sec is None):
        warnings.append("Clip query is missing a selected time window.")
        search_enabled = False
    elif (
        query_owner_type is OwnerType.CLIP
        and clip_start_sec is not None
        and clip_end_sec is not None
        and clip_end_sec <= clip_start_sec
    ):
        warnings.append("Clip query end must be after start.")
        search_enabled = False
    if query_owner_type is OwnerType.SOURCE and not _source_mode_enabled(mode, source_type):
        warnings.append("Selected source type is not compatible with this search mode.")
        search_enabled = False
    search_intent: SearchIntentDTO | None = None
    if search_enabled:
        from deep_sound.ui.library_workflow import SearchIntentDTO

        search_intent = SearchIntentDTO(query_id=query_owner_id, mode=mode.value)
    return DesktopQueryState(
        query_owner_id=query_owner_id,
        query_owner_type=query_owner_type,
        search_mode=mode,
        weights=_weights_for_mode(mode, current_weights),
        source_type=source_type,
        clip_start_sec=clip_start_sec,
        clip_end_sec=clip_end_sec,
        warnings=tuple(warnings),
        search_enabled=search_enabled,
        search_intent=search_intent,
    )


@dataclass(frozen=True, slots=True)
class InteractiveQueryBuilderState:
    selected_query_id: str | None
    selected_owner_type: OwnerType
    selected_search_mode: SearchMode
    weights: QueryWeights
    desktop_query: DesktopQueryState
    validation_messages: tuple[str, ...]
    can_search: bool


def interactive_query_builder_state(
    *,
    selected_query_id: str | None,
    selected_owner_type: OwnerType | str = OwnerType.TRACK,
    selected_search_mode: SearchMode | str = SearchMode.WEIGHTED,
    weights: QueryWeights | None = None,
    source_type: SourceType | None = None,
    clip_start_sec: float | None = None,
    clip_end_sec: float | None = None,
) -> InteractiveQueryBuilderState:
    owner_type = OwnerType(selected_owner_type)
    mode = SearchMode(selected_search_mode)
    current_weights = weights or QueryWeights()
    desktop_query = desktop_query_state(
        query_owner_id=selected_query_id or "",
        query_owner_type=owner_type,
        search_mode=mode,
        weights=current_weights,
        source_type=source_type,
        clip_start_sec=clip_start_sec,
        clip_end_sec=clip_end_sec,
    )
    return InteractiveQueryBuilderState(
        selected_query_id=selected_query_id,
        selected_owner_type=owner_type,
        selected_search_mode=mode,
        weights=current_weights,
        desktop_query=desktop_query,
        validation_messages=desktop_query.warnings,
        can_search=desktop_query.search_enabled,
    )


def _weights_for_mode(mode: SearchMode, weights: QueryWeights) -> dict[str, float]:
    if mode is SearchMode.WEIGHTED:
        return weights.normalized_phase5_weights()
    return {mode.value: 1.0}


def _source_mode_enabled(mode: SearchMode, source_type: SourceType | None) -> bool:
    phase3 = phase3_query_control_state(source_type)
    phase5 = phase5_query_control_state(source_type)
    if mode in {SearchMode.SOURCE_CHORDS, SearchMode.CHORD_CHANGE}:
        return phase3.source_chord_enabled
    if mode is SearchMode.MELODY:
        return phase5.melody_enabled
    if mode is SearchMode.VOCAL_TIMBRE:
        return phase5.vocal_timbre_enabled
    if mode is SearchMode.SOURCE_ROLE:
        return phase5.source_role_enabled
    return True


def phase5_query_control_state(source_type: SourceType | None) -> Phase5QueryControlState:
    source_compatible = source_type in {SourceType.MELODIC, SourceType.PITCHED_HARMONIC}
    return Phase5QueryControlState(
        production_enabled=True,
        structure_enabled=True,
        melody_enabled=source_compatible,
        vocal_timbre_enabled=source_compatible,
        source_role_enabled=source_compatible,
    )


@dataclass(frozen=True, slots=True)
class IndexStatusDTO:
    feature_type: FeatureType
    owner_type: OwnerType
    available: bool
    stale: bool
    backend: str
    feature_count: int
    dim: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndexedSearchResultMetadata:
    search_backend: str
    matched_entity_type: str | None
    matched_range: str | None
    dimension_scores: dict[str, float]
    caveats: tuple[str, ...] = ()
    feedback_adjustment: float = 0.0


@dataclass(frozen=True, slots=True)
class Phase3QueryControlState:
    selected_source_enabled: bool
    chord_change_enabled: bool
    source_chord_enabled: bool
    compatible_source_filter_enabled: bool


def phase3_query_control_state(source_type: SourceType | None) -> Phase3QueryControlState:
    enabled = source_type is SourceType.PITCHED_HARMONIC
    return Phase3QueryControlState(
        selected_source_enabled=enabled,
        chord_change_enabled=enabled,
        source_chord_enabled=enabled,
        compatible_source_filter_enabled=enabled,
    )


def create_query_builder_widget(weights: QueryWeights | None = None) -> object:
    """Create the PySide query builder widget.

    Later-phase controls are visible but disabled because source-specific chord
    and instrument behavior search is outside Phase 1.
    """
    try:
        from PySide6.QtGui import QStandardItemModel
        from PySide6.QtWidgets import (
            QCheckBox,
            QComboBox,
            QFormLayout,
            QGroupBox,
            QLabel,
            QPushButton,
            QSlider,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)

    target = QComboBox()
    target.addItems(["Whole track", "Selected clip", "Selected section"])
    target.addItem("Selected stem")
    target.addItem("Selected source")
    target_model = cast(QStandardItemModel, target.model())
    target_model.item(3).setEnabled(False)
    target_model.item(4).setEnabled(False)
    layout.addWidget(target)

    current = weights or QueryWeights()
    form = QFormLayout()
    for label, value, enabled in [
        ("Rhythm / groove", current.rhythm, True),
        ("Harmony chroma", current.harmony, True),
        ("Chord-change timing", current.chord_change, False),
        ("Instrument behavior", current.source_behavior, False),
        ("Timbre / production", current.timbre, True),
    ]:
        slider = QSlider()
        slider.setRange(0, 100)
        slider.setValue(int(value * 100))
        slider.setEnabled(enabled)
        form.addRow(QLabel(label), slider)
    layout.addLayout(form)

    options = QGroupBox("Normalization")
    option_layout = QVBoxLayout(options)
    for label, enabled, checked in [
        ("Key-invariant harmony", True, True),
        ("Tempo-scaled rhythm", True, True),
        ("Require same instrument label", False, False),
        ("Allow compatible source types", False, True),
    ]:
        checkbox = QCheckBox(label)
        checkbox.setChecked(checked)
        checkbox.setEnabled(enabled)
        option_layout.addWidget(checkbox)
    layout.addWidget(options)

    layout.addWidget(QPushButton("Search"))
    return root
