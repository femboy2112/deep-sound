"""AnalysisService — spec §10.2, §16.2. Phase 1 target."""

from __future__ import annotations

from deep_sound.domain.track import Track


class AnalysisService:
    """Orchestrates feature extraction and model inference for a track.

    Stub — implemented in Phase 1 (P1-003).
    """

    def analyze(self, track: Track) -> None:
        raise NotImplementedError("AnalysisService.analyze pending P1-003")
