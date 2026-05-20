"""Weighted query builder controls for Phase 1 similarity search."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueryWeights:
    rhythm: float = 0.25
    harmony: float = 0.25
    chord_change: float = 0.0
    source_behavior: float = 0.0
    timbre: float = 0.50

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


def create_query_builder_widget(weights: QueryWeights | None = None) -> object:
    """Create the PySide query builder widget.

    Later-phase controls are visible but disabled because source-specific chord
    and instrument behavior search is outside Phase 1.
    """
    try:
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]
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
    target.model().item(3).setEnabled(False)
    target.model().item(4).setEnabled(False)
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
