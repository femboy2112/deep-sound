"""Track detail view helpers for waveform, sections, and feature summaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from deep_sound.domain.feature_view import FeatureView
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SourceActivityRecord


@dataclass(frozen=True, slots=True)
class FeatureSummaryRow:
    feature_type: str
    algorithm: str
    confidence: str


def feature_summary_rows(features: Sequence[FeatureView]) -> list[FeatureSummaryRow]:
    return [
        FeatureSummaryRow(
            feature_type=feature.feature_type.value,
            algorithm=f"{feature.algorithm} v{feature.algorithm_version}",
            confidence="unknown"
            if feature.confidence is None
            else f"{feature.confidence.value:.2f}",
        )
        for feature in features
    ]


def create_track_detail_widget(
    track: Track,
    sections: Sequence[SectionRecord] = (),
    source_activity: Sequence[SourceActivityRecord] = (),
    features: Sequence[FeatureView] = (),
) -> object:
    """Create a PySide track-detail widget from service-level DTOs."""
    try:
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QPushButton,
            QSlider,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)
    title = track.title or track.filepath.stem
    layout.addWidget(QLabel(f"{title}  |  {track.analysis_status}"))

    controls = QHBoxLayout()
    controls.addWidget(QPushButton("Play"))
    controls.addWidget(QPushButton("Pause"))
    controls.addWidget(QPushButton("Analyze"))
    controls.addWidget(QPushButton("Reanalyze"))
    layout.addLayout(controls)

    waveform = QSlider()
    waveform.setRange(0, int(track.duration_sec or 0))
    layout.addWidget(waveform)

    section_box = QGroupBox("Sections")
    section_list = QListWidget()
    for section in sections:
        section_list.addItem(
            f"{section.label} {section.start_sec:.1f}-{section.end_sec:.1f}s "
            f"confidence {section.confidence.value:.2f}"
        )
    section_layout = QVBoxLayout(section_box)
    section_layout.addWidget(section_list)
    layout.addWidget(section_box)

    activity_box = QGroupBox("Source Activity")
    activity_list = QListWidget()
    for activity in source_activity:
        activity_list.addItem(
            f"{activity.source_id} {activity.start_sec:.1f}-{activity.end_sec:.1f}s "
            f"confidence {activity.confidence.value:.2f}"
        )
    activity_layout = QVBoxLayout(activity_box)
    activity_layout.addWidget(activity_list)
    layout.addWidget(activity_box)

    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["Feature", "Algorithm", "Confidence"])
    for row in feature_summary_rows(features):
        index = table.rowCount()
        table.insertRow(index)
        for column, value in enumerate([row.feature_type, row.algorithm, row.confidence]):
            table.setItem(index, column, QTableWidgetItem(value))
    layout.addWidget(table)
    return root
