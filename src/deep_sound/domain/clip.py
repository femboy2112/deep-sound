"""Clip windows selected by users for query-focused analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClipWindow:
    id: str
    track_id: str
    start_sec: float
    end_sec: float
    label: str | None = None

    def __post_init__(self) -> None:
        if self.start_sec < 0.0:
            raise ValueError("ClipWindow.start_sec must be non-negative")
        if self.end_sec <= self.start_sec:
            raise ValueError("ClipWindow.end_sec must be greater than start_sec")
