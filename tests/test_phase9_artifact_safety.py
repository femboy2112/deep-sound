from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_service import LibraryService
from deep_sound.services.waveform_service import WaveformService


def test_waveform_artifacts_stay_under_app_data_and_original_audio_is_unchanged(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "song.wav"
    _write_tone(audio_path)
    original_hash = _sha256(audio_path)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = LibraryService(store).import_file(audio_path)
    app_data_dir = tmp_path / "app_data"

    cache = WaveformService(app_data_dir).build_cache(track)

    assert cache.artifact_path.is_relative_to(app_data_dir)
    assert cache.artifact_path.exists()
    assert cache.algorithm
    assert cache.version
    assert _sha256(audio_path) == original_hash


def _write_tone(path: Path) -> None:
    sample_rate = 22050
    duration_sec = 1.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    samples = (0.2 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    sf.write(path, samples, sample_rate)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
