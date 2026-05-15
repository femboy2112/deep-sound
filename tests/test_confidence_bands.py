"""Boundary tests for the Confidence value object. Spec §23.2."""

from __future__ import annotations

import math

import pytest

from deep_sound.domain.confidence import Confidence, ConfidenceBand


def test_clamps_above_one() -> None:
    assert Confidence(1.5).value == 1.0


def test_clamps_below_zero() -> None:
    assert Confidence(-0.3).value == 0.0


def test_rejects_nan() -> None:
    with pytest.raises(ValueError):
        Confidence(math.nan)


@pytest.mark.parametrize(
    "value, expected",
    [
        (1.0, ConfidenceBand.HIGH),
        (0.8, ConfidenceBand.HIGH),
        (0.79, ConfidenceBand.MEDIUM),
        (0.6, ConfidenceBand.MEDIUM),
        (0.59, ConfidenceBand.LOW),
        (0.4, ConfidenceBand.LOW),
        (0.39, ConfidenceBand.VERY_UNCERTAIN),
        (0.0, ConfidenceBand.VERY_UNCERTAIN),
    ],
)
def test_band_boundaries(value: float, expected: ConfidenceBand) -> None:
    assert Confidence(value).band is expected


def test_very_uncertain_hidden_by_default() -> None:
    assert Confidence(0.2).visible_by_default is False
    assert Confidence(0.5).visible_by_default is True
