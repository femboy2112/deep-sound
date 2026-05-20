from __future__ import annotations

import pytest

from deep_sound.domain.corrections import (
    ResultFeedbackPayload,
    ResultFeedbackValue,
    SourceCorrectionPayload,
    bounded_feedback_adjustment,
    clamp_score,
)
from deep_sound.domain.source import SourceType


def test_source_correction_payload_requires_meaningful_change() -> None:
    with pytest.raises(ValueError, match="requires"):
        SourceCorrectionPayload()
    with pytest.raises(ValueError, match="blank"):
        SourceCorrectionPayload(label="  ")

    payload = SourceCorrectionPayload(label="likely guitar", source_type=SourceType.MELODIC)

    assert payload.label == "likely guitar"
    assert payload.source_type is SourceType.MELODIC


def test_result_feedback_payload_validates_result_owner() -> None:
    with pytest.raises(ValueError, match="result_owner_id"):
        ResultFeedbackPayload(result_owner_id="", feedback=ResultFeedbackValue.RELEVANT)


def test_feedback_adjustment_is_bounded_and_scores_are_clamped() -> None:
    assert bounded_feedback_adjustment(3, 0) == 0.10
    assert bounded_feedback_adjustment(0, 3) == -0.10
    assert bounded_feedback_adjustment(1, 0) == 0.05
    assert clamp_score(1.4) == 1.0
    assert clamp_score(-0.4) == 0.0
