from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_service import LibraryImportError, LibraryService


def test_import_file_extracts_metadata_and_preserves_original(tmp_path: Path) -> None:
    audio_path = _write_tone(tmp_path / "example.wav")
    before_bytes = audio_path.read_bytes()
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = LibraryService(store)

    track = service.import_file(audio_path)

    assert track.filepath == audio_path.resolve()
    assert track.title == "example"
    assert track.duration_sec == pytest.approx(1.0)
    assert track.sample_rate == 22050
    assert track.audio_hash == hashlib.sha256(before_bytes).hexdigest()
    assert track.import_status == "imported"
    assert track.analysis_status == "pending"
    assert audio_path.read_bytes() == before_bytes


def test_import_file_dedupes_by_sha256(tmp_path: Path) -> None:
    first = _write_tone(tmp_path / "first.wav")
    duplicate = tmp_path / "duplicate.wav"
    shutil.copyfile(first, duplicate)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = LibraryService(store)

    first_track = service.import_file(first)
    duplicate_track = service.import_file(duplicate)

    assert duplicate_track == first_track
    assert len(store.list_tracks()) == 1


def test_import_folder_recurses_and_continues_after_failed_file(tmp_path: Path) -> None:
    _write_tone(tmp_path / "root.wav", frequency=220.0)
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_tone(nested / "child.wav", frequency=330.0)
    broken = nested / "broken.wav"
    broken.write_text("not audio", encoding="utf-8")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = LibraryService(store)

    tracks = service.import_folder(tmp_path)

    assert [track.title for track in tracks] == ["child", "root"]
    assert len(store.list_tracks()) == 2
    failed_jobs = store.list_jobs(status="failed")
    assert len(failed_jobs) == 1
    assert failed_jobs[0].target_id == str(broken.resolve())


def test_import_folder_non_recursive_skips_nested_files(tmp_path: Path) -> None:
    _write_tone(tmp_path / "root.wav", frequency=220.0)
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_tone(nested / "child.wav", frequency=330.0)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = LibraryService(store)

    tracks = service.import_folder(tmp_path, recursive=False)

    assert [track.title for track in tracks] == ["root"]


def test_import_file_failure_records_failed_job(tmp_path: Path) -> None:
    broken = tmp_path / "broken.wav"
    broken.write_text("not audio", encoding="utf-8")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = LibraryService(store)

    with pytest.raises(LibraryImportError):
        service.import_file(broken)

    failed_jobs = store.list_jobs(status="failed")
    assert len(failed_jobs) == 1
    assert failed_jobs[0].target_id == str(broken.resolve())
    assert store.list_tracks() == []


def _write_tone(path: Path, frequency: float = 440.0, sample_rate: int = 22050) -> Path:
    duration_sec = 1.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (0.1 * np.sin(2.0 * np.pi * frequency * t)).astype(np.float32)
    sf.write(path, audio, sample_rate)
    return path
