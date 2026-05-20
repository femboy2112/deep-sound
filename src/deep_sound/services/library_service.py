"""LibraryService — spec §10.2, §16.1. Phase 1 target."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

import soundfile as sf

from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore


class LibraryImportError(RuntimeError):
    """Raised when an individual file cannot be imported."""


class LibraryService:
    """File import, metadata extraction, dedupe, and analysis-status tracking."""

    AUDIO_SUFFIXES = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".wav"})

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def import_file(self, path: Path) -> Track:
        audio_path = path.expanduser().resolve()
        if not audio_path.is_file():
            self._record_failed_import(audio_path, "File does not exist or is not a file")
            raise LibraryImportError(f"Audio file not found: {audio_path}")

        try:
            audio_hash = sha256_file(audio_path)
            existing = self._store.get_track_by_hash(audio_hash)
            if existing is not None:
                return existing

            info = sf.info(str(audio_path))
            track = Track(
                id=str(uuid4()),
                filepath=audio_path,
                title=audio_path.stem,
                artist=None,
                album=None,
                duration_sec=float(info.duration),
                sample_rate=int(info.samplerate),
                audio_hash=audio_hash,
                import_status="imported",
                analysis_status="pending",
            )
            return self._store.add_track(track)
        except Exception as exc:
            if isinstance(exc, LibraryImportError):
                raise
            self._record_failed_import(audio_path, str(exc))
            raise LibraryImportError(f"Could not import audio file {audio_path}: {exc}") from exc

    def import_folder(self, path: Path, recursive: bool = True) -> list[Track]:
        folder = path.expanduser().resolve()
        if not folder.is_dir():
            self._record_failed_import(folder, "Folder does not exist or is not a directory")
            raise LibraryImportError(f"Import folder not found: {folder}")

        imported: list[Track] = []
        for audio_path in self._iter_audio_files(folder, recursive=recursive):
            try:
                imported.append(self.import_file(audio_path))
            except LibraryImportError:
                continue
        return imported

    def _iter_audio_files(self, folder: Path, *, recursive: bool) -> Iterable[Path]:
        paths = folder.rglob("*") if recursive else folder.iterdir()
        for candidate in sorted(paths):
            if candidate.is_file() and candidate.suffix.lower() in self.AUDIO_SUFFIXES:
                yield candidate

    def _record_failed_import(self, path: Path, error_message: str) -> None:
        self._store.create_job(
            job_type="import_file",
            target_type="file",
            target_id=str(path),
            status="failed",
            progress=1.0,
            error_message=error_message,
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
