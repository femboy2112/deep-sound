"""AnalysisService — spec §10.2, §16.2. Phase 1 full-mix extraction."""

from __future__ import annotations

from collections.abc import Callable

from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.analyzers.chroma_librosa import summarize_chroma
from deep_sound.infra.analyzers.mfcc_librosa import summarize_mfcc
from deep_sound.infra.analyzers.tempo_librosa import DEFAULT_SAMPLE_RATE, estimate_tempo
from deep_sound.infra.storage.sqlite_store import SqliteStore

ProgressCallback = Callable[[str, float], None]


class AnalysisService:
    """Orchestrates Phase 1 full-mix feature extraction for a track."""

    def __init__(
        self,
        store: SqliteStore,
        *,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._store = store
        self._sample_rate = sample_rate
        self._progress_callback = progress_callback

    def analyze(self, track: Track) -> list[FeatureView]:
        """Extract and persist rhythm, chroma, and MFCC views for a track.

        Phase 1 deliberately stays at the full-mix track level. Source, stem,
        chord, and section-level feature views are later phases.
        """
        self._emit_progress("started", 0.0)

        tempo = estimate_tempo(track.filepath, sample_rate=self._sample_rate)
        rhythm = FeatureView(
            id=f"{track.id}:rhythm.global",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.RHYTHM_GLOBAL,
            algorithm=tempo.analyzer,
            algorithm_version=tempo.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats={
                "tempo_bpm": tempo.tempo_bpm,
                "beats_per_sec": len(tempo.beats_sec) / max(tempo.duration_sec, 1.0),
            },
            confidence=tempo.confidence,
        )
        self._store.add_feature_view(rhythm)
        self._emit_progress("rhythm.global", 1.0 / 3.0)

        chroma = summarize_chroma(track.filepath, sample_rate=self._sample_rate)
        harmony = FeatureView(
            id=f"{track.id}:harmony.chroma",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.HARMONY_CHROMA,
            algorithm=chroma.analyzer,
            algorithm_version=chroma.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate}",
            stats=_vector_stats("chroma", chroma.chroma),
            confidence=chroma.confidence,
        )
        self._store.add_feature_view(harmony)
        self._emit_progress("harmony.chroma", 2.0 / 3.0)

        mfcc = summarize_mfcc(track.filepath, sample_rate=self._sample_rate)
        timbre = FeatureView(
            id=f"{track.id}:timbre.mfcc_stats",
            owner_type=OwnerType.TRACK,
            owner_id=track.id,
            feature_type=FeatureType.TIMBRE_MFCC_STATS,
            algorithm=mfcc.analyzer,
            algorithm_version=mfcc.analyzer_version,
            params_hash=f"sample_rate={self._sample_rate};n_mfcc={mfcc.n_mfcc}",
            stats=_vector_stats("mfcc", mfcc.mfcc),
            confidence=mfcc.confidence,
        )
        self._store.add_feature_view(timbre)
        self._emit_progress("timbre.mfcc_stats", 1.0)

        return [rhythm, harmony, timbre]

    def _emit_progress(self, stage: str, progress: float) -> None:
        if self._progress_callback is not None:
            self._progress_callback(stage, progress)


def _vector_stats(prefix: str, values: list[float]) -> dict[str, float]:
    return {f"{prefix}_{index:02d}": value for index, value in enumerate(values)}
