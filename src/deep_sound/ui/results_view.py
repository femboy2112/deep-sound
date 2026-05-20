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
    query_owner_id: str | None = None
    result_owner_id: str | None = None
    matched_entity_type: str | None = None
    matched_range: str | None = None
    matched_source: str | None = None
    matched_stem: str | None = None
    baseline_score: float | None = None
    feedback_adjustment: float = 0.0
    search_backend: str = "scan"
    stale_index_warnings: tuple[str, ...] = field(default_factory=tuple)
    caveats: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def confidence_warnings(
    dimension_scores: dict[str, float], threshold: float = 0.5
) -> tuple[str, ...]:
    return tuple(
        f"{name} similarity evidence is weak ({score:.2f})"
        for name, score in sorted(dimension_scores.items())
        if score < threshold
    )


@dataclass(frozen=True, slots=True)
class ResultFeedbackActionData:
    query_owner_id: str
    result_owner_id: str
    relevant_value: str = "relevant"
    irrelevant_value: str = "irrelevant"


def result_feedback_action(card: ResultCardData) -> ResultFeedbackActionData | None:
    if card.query_owner_id is None or card.result_owner_id is None:
        return None
    return ResultFeedbackActionData(
        query_owner_id=card.query_owner_id,
        result_owner_id=card.result_owner_id,
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
        card_layout.addWidget(QLabel(f"Backend: {card.search_backend}"))
        if card.baseline_score is not None or card.feedback_adjustment:
            baseline = "-" if card.baseline_score is None else f"{card.baseline_score:.0%}"
            card_layout.addWidget(
                QLabel(f"Baseline: {baseline}  feedback adjustment {card.feedback_adjustment:+.2f}")
            )
        scores = ", ".join(
            f"{name} {score:.0%}" for name, score in sorted(card.dimension_scores.items())
        )
        card_layout.addWidget(QLabel(scores))
        for warning in card.stale_index_warnings:
            card_layout.addWidget(QLabel(f"Index warning: {warning}"))
        for caveat in card.caveats:
            card_layout.addWidget(QLabel(f"Caveat: {caveat}"))
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
