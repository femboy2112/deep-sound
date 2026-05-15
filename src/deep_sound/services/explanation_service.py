"""ExplanationService — spec §10.2, §14.8, §16.6. Phase 1 target."""

from __future__ import annotations


class ExplanationService:
    """Convert technical score details into human-readable explanations.

    Stub — implemented in Phase 1 (P1-010).
    """

    def summarize(self, scores: dict[str, float]) -> str:
        raise NotImplementedError("ExplanationService.summarize pending P1-010")
