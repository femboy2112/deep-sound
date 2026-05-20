"""Waveform cache artifacts and import-safe DTOs for clip workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.clip import ClipWindow
from deep_sound.domain.track import Track

WAVEFORM_CACHE_VERSION = "waveform-cache-v1"


@dataclass(frozen=True, slots=True)
class WaveformPointDTO:
    start_sec: float
    end_sec: float
    min_amplitude: float
    max_amplitude: float
    rms: float


@dataclass(frozen=True, slots=True)
class WaveformCacheDTO:
    track_id: str
    artifact_path: Path
    duration_sec: float
    sample_rate: int
    algorithm: str
    version: str
    points: tuple[WaveformPointDTO, ...]


@dataclass(frozen=True, slots=True)
class ClipWindowDTO:
    id: str
    track_id: str
    start_sec: float
    end_sec: float
    label: str | None = None


class WaveformService:
    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root

    def build_cache(self, track: Track, *, point_count: int = 512) -> WaveformCacheDTO:
        if point_count <= 0:
            raise ValueError("point_count must be positive")
        data, sample_rate = sf.read(str(track.filepath), always_2d=True)
        mono = np.asarray(np.mean(data, axis=1), dtype=np.float64)
        duration_sec = float(len(mono) / sample_rate) if sample_rate > 0 else 0.0
        points = _waveform_points(mono, sample_rate, point_count)
        artifact_path = self._cache_root / "waveforms" / f"{track.id}.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "track_id": track.id,
            "duration_sec": duration_sec,
            "sample_rate": int(sample_rate),
            "algorithm": "soundfile_peak_rms_summary",
            "version": WAVEFORM_CACHE_VERSION,
            "points": [asdict(point) for point in points],
        }
        artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return WaveformCacheDTO(
            track_id=track.id,
            artifact_path=artifact_path,
            duration_sec=duration_sec,
            sample_rate=int(sample_rate),
            algorithm=str(payload["algorithm"]),
            version=WAVEFORM_CACHE_VERSION,
            points=tuple(points),
        )


def clip_window_dto(clip: ClipWindow) -> ClipWindowDTO:
    return ClipWindowDTO(
        id=clip.id,
        track_id=clip.track_id,
        start_sec=clip.start_sec,
        end_sec=clip.end_sec,
        label=clip.label,
    )


def _waveform_points(
    mono: np.ndarray,
    sample_rate: int,
    point_count: int,
) -> list[WaveformPointDTO]:
    if mono.size == 0 or sample_rate <= 0:
        return []
    chunk_count = min(point_count, mono.size)
    edges = np.linspace(0, mono.size, chunk_count + 1, dtype=int)
    points: list[WaveformPointDTO] = []
    for left, right in pairwise(edges):
        if right <= left:
            continue
        chunk = mono[left:right]
        points.append(
            WaveformPointDTO(
                start_sec=float(left / sample_rate),
                end_sec=float(right / sample_rate),
                min_amplitude=float(np.min(chunk)),
                max_amplitude=float(np.max(chunk)),
                rms=float(np.sqrt(np.mean(np.square(chunk)))),
            )
        )
    return points
