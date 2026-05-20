"""SimilarityService — spec §10.2, §14, §16.5. Phase 0 cosine, Phase 1 FAISS."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.services.feature_service import FeatureService


class SearchMode(StrEnum):
    RHYTHM = "rhythm"
    HARMONY = "harmony"
    TIMBRE = "timbre"
    WEIGHTED = "weighted"


MODE_FEATURE_TYPES: dict[SearchMode, tuple[FeatureType, ...]] = {
    SearchMode.RHYTHM: (FeatureType.RHYTHM_GLOBAL,),
    SearchMode.HARMONY: (FeatureType.HARMONY_CHROMA,),
    SearchMode.TIMBRE: (FeatureType.TIMBRE_MFCC_STATS,),
    SearchMode.WEIGHTED: (
        FeatureType.RHYTHM_GLOBAL,
        FeatureType.HARMONY_CHROMA,
        FeatureType.TIMBRE_MFCC_STATS,
    ),
}


@dataclass(frozen=True, slots=True)
class SimilarityResult:
    owner_id: str
    score: float
    dimension_scores: dict[str, float]
    owner_type: OwnerType = OwnerType.TRACK
    matched_stem: str | None = None
    matched_range: str | None = None
    caveats: tuple[str, ...] = ()


class SimilarityService:
    """Candidate retrieval + weighted combined scoring over in-memory vectors."""

    def __init__(self, features: FeatureService) -> None:
        self._features = features

    def search(
        self,
        query_id: str,
        weights: dict[str, float],
        top_k: int = 10,
        owner_type: OwnerType | None = None,
    ) -> list[SimilarityResult]:
        """Rank feature owners against `query_id`.

        Weight keys may be short mode names (`rhythm`) or feature type values
        (`rhythm.global`). Empty weights default to equal Phase 0 weighting.
        """
        normalized_weights = self._normalize_weights(weights)
        query_views = self._features.list_by_owner(query_id)
        if not query_views:
            raise KeyError(f"No features found for query owner: {query_id}")

        candidate_ids: set[str] = set()
        candidate_owner_types: dict[str, OwnerType] = {}
        for feature_type in normalized_weights:
            for view in self._features.list_by_type(feature_type):
                if view.owner_id == query_id:
                    continue
                if owner_type is not None and view.owner_type is not owner_type:
                    continue
                candidate_ids.add(view.owner_id)
                candidate_owner_types[view.owner_id] = view.owner_type

        results: list[SimilarityResult] = []
        for candidate_id in sorted(candidate_ids):
            dimension_scores: dict[str, float] = {}
            weighted_total = 0.0
            weight_total = 0.0
            for feature_type, weight in normalized_weights.items():
                score = self._score_dimension(query_id, candidate_id, feature_type)
                if score is None:
                    continue
                dimension_scores[feature_type.value] = score
                weighted_total += weight * score
                weight_total += weight
            if weight_total <= 0.0:
                continue
            results.append(
                SimilarityResult(
                    owner_id=candidate_id,
                    score=weighted_total / weight_total,
                    dimension_scores=dimension_scores,
                    owner_type=candidate_owner_types.get(candidate_id, OwnerType.TRACK),
                    matched_stem=candidate_id
                    if candidate_owner_types.get(candidate_id) is OwnerType.STEM
                    else None,
                    matched_range="full stem"
                    if candidate_owner_types.get(candidate_id) is OwnerType.STEM
                    else None,
                    caveats=("Stem-level match is probabilistic.",)
                    if candidate_owner_types.get(candidate_id) is OwnerType.STEM
                    else (),
                )
            )

        return sorted(results, key=lambda result: (-result.score, result.owner_id))[:top_k]

    def search_mode(
        self,
        query_id: str,
        mode: SearchMode,
        top_k: int = 10,
    ) -> list[SimilarityResult]:
        return self.search(
            query_id=query_id,
            weights={feature_type.value: 1.0 for feature_type in MODE_FEATURE_TYPES[mode]},
            top_k=top_k,
        )

    def search_stems(
        self,
        query_id: str,
        weights: dict[str, float],
        top_k: int = 10,
    ) -> list[SimilarityResult]:
        return self.search(
            query_id=query_id,
            weights=weights,
            top_k=top_k,
            owner_type=OwnerType.STEM,
        )

    def _score_dimension(
        self,
        query_id: str,
        candidate_id: str,
        feature_type: FeatureType,
    ) -> float | None:
        try:
            query_view = self._features.get_for_owner(query_id, feature_type)
            candidate_view = self._features.get_for_owner(candidate_id, feature_type)
        except KeyError:
            return None
        return cosine_score(
            self._features.vector_for(query_view),
            self._features.vector_for(candidate_view),
        )

    def _normalize_weights(self, weights: dict[str, float]) -> dict[FeatureType, float]:
        if not weights:
            return {feature_type: 1.0 for feature_type in MODE_FEATURE_TYPES[SearchMode.WEIGHTED]}

        normalized: dict[FeatureType, float] = {}
        for raw_key, raw_weight in weights.items():
            weight = float(raw_weight)
            if weight <= 0.0:
                continue
            feature_types = self._feature_types_for_key(raw_key)
            for feature_type in feature_types:
                normalized[feature_type] = normalized.get(feature_type, 0.0) + weight
        if not normalized:
            raise ValueError("At least one positive similarity weight is required")
        return normalized

    def _feature_types_for_key(self, key: str) -> tuple[FeatureType, ...]:
        with_context = f"Unsupported similarity weight key: {key}"
        try:
            mode = SearchMode(key)
        except ValueError:
            mode = None
        if mode is not None:
            return MODE_FEATURE_TYPES[mode]
        try:
            return (FeatureType(key),)
        except ValueError as exc:
            raise ValueError(with_context) from exc


def cosine_score(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare vectors with different lengths")
    if not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))
