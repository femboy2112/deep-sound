"""Confidence value object — spec §3.3 and §23.2.

Every inferred label (sources, chords, sections, events) must carry a
confidence in [0, 1]. The UI displays one of four bands.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_UNCERTAIN = "very_uncertain"


@dataclass(frozen=True, slots=True)
class Confidence:
    """A bounded confidence score with a display band.

    Range: [0.0, 1.0]. Values outside are clamped. Spec section 23.2 bands:
      0.80-1.00 high
      0.60-0.79 medium
      0.40-0.59 low
      < 0.40    very uncertain (hidden by default)
    """

    value: float

    def __post_init__(self) -> None:
        if self.value != self.value:  # NaN check
            raise ValueError("Confidence value cannot be NaN")
        clamped = max(0.0, min(1.0, float(self.value)))
        # Frozen dataclass — set via object.__setattr__
        object.__setattr__(self, "value", clamped)

    @property
    def band(self) -> ConfidenceBand:
        if self.value >= 0.80:
            return ConfidenceBand.HIGH
        if self.value >= 0.60:
            return ConfidenceBand.MEDIUM
        if self.value >= 0.40:
            return ConfidenceBand.LOW
        return ConfidenceBand.VERY_UNCERTAIN

    @property
    def visible_by_default(self) -> bool:
        """Spec §23.2: very-uncertain claims hidden unless diagnostics enabled."""
        return self.band is not ConfidenceBand.VERY_UNCERTAIN

    def __str__(self) -> str:
        return f"{self.value:.2f}"
