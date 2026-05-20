"""ExplanationService — cautious summaries for similarity score details."""

from __future__ import annotations

from collections.abc import Mapping

from deep_sound.services.similarity_service import SimilarityResult

LOW_CONFIDENCE_THRESHOLD = 0.4


class ExplanationService:
    """Convert technical score details into human-readable explanations."""

    def summarize(self, result: SimilarityResult | Mapping[str, float]) -> str:
        """Return cautious text for a ranked result or raw dimension scores."""
        owner_id: str | None
        overall: float | None
        scores: Mapping[str, float]
        if isinstance(result, SimilarityResult):
            owner_id = result.owner_id
            overall = result.score
            scores = result.dimension_scores
        else:
            owner_id = None
            overall = None
            scores = result

        if not scores:
            target = f"{owner_id} " if owner_id is not None else ""
            return f"{target}has no comparable score details yet; treat the match as uncertain."

        ranked_scores = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        strongest_name, strongest_score = ranked_scores[0]
        parts: list[str] = []
        if owner_id is not None and overall is not None:
            parts.append(f"{owner_id} is a possible match with overall score {overall:.2f}.")
        elif overall is not None:
            parts.append(f"Possible match with overall score {overall:.2f}.")
        else:
            parts.append("Possible match based on available score details.")

        parts.append(
            f"The strongest evidence is {strongest_name} similarity at {strongest_score:.2f}."
        )
        if isinstance(result, SimilarityResult) and result.matched_stem is not None:
            parts.append(
                f"The matched stem is {result.matched_stem}; treat stem identity as probabilistic."
            )
        if isinstance(result, SimilarityResult) and result.matched_range is not None:
            parts.append(f"The matched range is {result.matched_range}.")
        if len(ranked_scores) > 1:
            supporting = ", ".join(f"{name} {score:.2f}" for name, score in ranked_scores[1:3])
            parts.append(f"Other observed dimensions are {supporting}.")

        low_scores = [name for name, score in ranked_scores if score < LOW_CONFIDENCE_THRESHOLD]
        if low_scores:
            parts.append(
                "Low-confidence or weak dimensions "
                f"({', '.join(low_scores)}) should be used cautiously."
            )
        else:
            parts.append("This is similarity evidence, not a definitive identification.")
        if isinstance(result, SimilarityResult) and result.caveats:
            parts.append(" ".join(result.caveats))
        return " ".join(parts)
