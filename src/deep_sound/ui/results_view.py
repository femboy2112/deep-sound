"""Search result cards for Phase 1 desktop UI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ResultCardData:
    track_title: str
    artist: str | None
    combined_score: float
    dimension_scores: dict[str, float]
    explanation: str
    matched_range: str | None = None
    matched_source: str | None = None
    baseline_score: float | None = None
    feedback_adjustment: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)


def confidence_warnings(
    dimension_scores: dict[str, float], threshold: float = 0.5
) -> tuple[str, ...]:
    return tuple(
        f"{name} is low-confidence ({score:.2f})"
        for name, score in sorted(dimension_scores.items())
        if score < threshold
    )


def create_results_view(cards: Sequence[ResultCardData]) -> object:
    """Create a PySide results list from result-card DTOs."""
    try:
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]
            QFrame,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)
    for card in cards:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout(frame)
        artist = card.artist or "Unknown artist"
        card_layout.addWidget(
            QLabel(f"{card.track_title} - {artist}  score {card.combined_score:.0%}")
        )
        if card.matched_range:
            card_layout.addWidget(QLabel(f"Range: {card.matched_range}"))
        if card.matched_source:
            card_layout.addWidget(QLabel(f"Source: {card.matched_source}"))
        scores = ", ".join(
            f"{name} {score:.0%}" for name, score in sorted(card.dimension_scores.items())
        )
        card_layout.addWidget(QLabel(scores))
        for warning in card.warnings:
            card_layout.addWidget(QLabel(warning))
        card_layout.addWidget(QLabel(card.explanation))

        actions = QHBoxLayout()
        actions.addWidget(QPushButton("Preview"))
        actions.addWidget(QPushButton("Compare"))
        actions.addWidget(QPushButton("Relevant"))
        actions.addWidget(QPushButton("Irrelevant"))
        card_layout.addLayout(actions)
        layout.addWidget(frame)
    return root
