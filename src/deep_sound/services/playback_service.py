"""Import-safe playback inspection service.

The default service is a deterministic state machine over imported tracks. It
does not import PySide, open audio devices, or write to original audio files.
UI adapters may wrap it with a real transport later while preserving this
contract for default verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from deep_sound.domain.track import Track


class PlaybackStatus(StrEnum):
    STOPPED = "stopped"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PlaybackState:
    track_id: str | None
    source_path: Path | None
    status: PlaybackStatus
    position_sec: float = 0.0
    duration_sec: float | None = None
    backend: str = "inspection"
    is_output_active: bool = False
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class PlaybackRequest:
    track: Track
    position_sec: float = 0.0


class PlaybackTransport(Protocol):
    @property
    def state(self) -> PlaybackState: ...

    def prepare(self, request: PlaybackRequest) -> PlaybackState: ...

    def play(self, request: PlaybackRequest) -> PlaybackState: ...

    def pause(self) -> PlaybackState: ...

    def seek(self, position_sec: float) -> PlaybackState: ...

    def stop(self) -> PlaybackState: ...


class PlaybackService:
    """A guarded playback seam suitable for default tests and UI wiring."""

    backend_name = "inspection"

    def __init__(self) -> None:
        self._state = PlaybackState(
            track_id=None,
            source_path=None,
            status=PlaybackStatus.STOPPED,
            backend=self.backend_name,
        )

    @property
    def state(self) -> PlaybackState:
        return self._state

    def prepare(self, request: PlaybackRequest) -> PlaybackState:
        position = _clamp_position(request.position_sec, request.track.duration_sec)
        if not request.track.filepath.exists():
            self._state = PlaybackState(
                track_id=request.track.id,
                source_path=request.track.filepath,
                status=PlaybackStatus.FAILED,
                position_sec=position,
                duration_sec=request.track.duration_sec,
                backend=self.backend_name,
                error_message=f"Audio file not found: {request.track.filepath}",
            )
            return self._state
        self._state = PlaybackState(
            track_id=request.track.id,
            source_path=request.track.filepath,
            status=PlaybackStatus.READY,
            position_sec=position,
            duration_sec=request.track.duration_sec,
            backend=self.backend_name,
        )
        return self._state

    def play(self, request: PlaybackRequest) -> PlaybackState:
        prepared = self.prepare(request)
        if prepared.status is PlaybackStatus.FAILED:
            return prepared
        self._state = PlaybackState(
            track_id=prepared.track_id,
            source_path=prepared.source_path,
            status=PlaybackStatus.PLAYING,
            position_sec=prepared.position_sec,
            duration_sec=prepared.duration_sec,
            backend=self.backend_name,
            is_output_active=False,
        )
        return self._state

    def pause(self) -> PlaybackState:
        if self._state.status is PlaybackStatus.FAILED:
            return self._state
        self._state = PlaybackState(
            track_id=self._state.track_id,
            source_path=self._state.source_path,
            status=PlaybackStatus.PAUSED if self._state.track_id else PlaybackStatus.STOPPED,
            position_sec=self._state.position_sec,
            duration_sec=self._state.duration_sec,
            backend=self.backend_name,
            is_output_active=False,
        )
        return self._state

    def seek(self, position_sec: float) -> PlaybackState:
        if self._state.track_id is None or self._state.status is PlaybackStatus.FAILED:
            return self._state
        self._state = PlaybackState(
            track_id=self._state.track_id,
            source_path=self._state.source_path,
            status=self._state.status,
            position_sec=_clamp_position(position_sec, self._state.duration_sec),
            duration_sec=self._state.duration_sec,
            backend=self.backend_name,
            is_output_active=self._state.is_output_active,
        )
        return self._state

    def stop(self) -> PlaybackState:
        self._state = PlaybackState(
            track_id=self._state.track_id,
            source_path=self._state.source_path,
            status=PlaybackStatus.STOPPED,
            position_sec=0.0,
            duration_sec=self._state.duration_sec,
            backend=self.backend_name,
            is_output_active=False,
        )
        return self._state


class LocalPlaybackAdapter(PlaybackService):
    """Guarded local audio adapter.

    Default construction never opens an audio device. Set
    ``audio_output_enabled=True`` only for explicit local live smoke sessions.
    """

    backend_name = "local-sounddevice"

    def __init__(self, *, audio_output_enabled: bool = False) -> None:
        super().__init__()
        self._audio_output_enabled = audio_output_enabled

    def play(self, request: PlaybackRequest) -> PlaybackState:
        prepared = self.prepare(request)
        if prepared.status is PlaybackStatus.FAILED:
            return prepared
        if not self._audio_output_enabled:
            self._state = PlaybackState(
                track_id=prepared.track_id,
                source_path=prepared.source_path,
                status=PlaybackStatus.PLAYING,
                position_sec=prepared.position_sec,
                duration_sec=prepared.duration_sec,
                backend=self.backend_name,
                is_output_active=False,
            )
            return self._state
        try:
            self._start_audio_output(request.track.filepath, prepared.position_sec)
        except Exception as exc:
            self._state = PlaybackState(
                track_id=prepared.track_id,
                source_path=prepared.source_path,
                status=PlaybackStatus.FAILED,
                position_sec=prepared.position_sec,
                duration_sec=prepared.duration_sec,
                backend=self.backend_name,
                is_output_active=False,
                error_message=str(exc),
            )
            return self._state
        self._state = PlaybackState(
            track_id=prepared.track_id,
            source_path=prepared.source_path,
            status=PlaybackStatus.PLAYING,
            position_sec=prepared.position_sec,
            duration_sec=prepared.duration_sec,
            backend=self.backend_name,
            is_output_active=True,
        )
        return self._state

    def pause(self) -> PlaybackState:
        if self._audio_output_enabled:
            try:
                self._stop_audio_output()
            except Exception as exc:
                self._state = self._failed_state(str(exc))
                return self._state
        return super().pause()

    def seek(self, position_sec: float) -> PlaybackState:
        if self._state.track_id is None or self._state.status is PlaybackStatus.FAILED:
            return self._state
        was_playing = self._state.status is PlaybackStatus.PLAYING
        source_path = self._state.source_path
        state = super().seek(position_sec)
        if not self._audio_output_enabled or not was_playing or source_path is None:
            return state
        try:
            self._stop_audio_output()
            self._start_audio_output(source_path, state.position_sec)
        except Exception as exc:
            self._state = self._failed_state(str(exc))
            return self._state
        self._state = PlaybackState(
            track_id=state.track_id,
            source_path=state.source_path,
            status=PlaybackStatus.PLAYING,
            position_sec=state.position_sec,
            duration_sec=state.duration_sec,
            backend=self.backend_name,
            is_output_active=True,
        )
        return self._state

    def stop(self) -> PlaybackState:
        if self._audio_output_enabled:
            try:
                self._stop_audio_output()
            except Exception as exc:
                self._state = self._failed_state(str(exc))
                return self._state
        return super().stop()

    def _start_audio_output(self, source_path: Path, position_sec: float) -> None:
        sf = import_module("soundfile")
        sd = import_module("sounddevice")
        data, sample_rate = sf.read(str(source_path), always_2d=True)
        start_frame = max(0, round(position_sec * sample_rate))
        cast(Any, sd).play(data[start_frame:], sample_rate, blocking=False)

    def _stop_audio_output(self) -> None:
        sd = import_module("sounddevice")
        cast(Any, sd).stop()

    def _failed_state(self, error_message: str) -> PlaybackState:
        return PlaybackState(
            track_id=self._state.track_id,
            source_path=self._state.source_path,
            status=PlaybackStatus.FAILED,
            position_sec=self._state.position_sec,
            duration_sec=self._state.duration_sec,
            backend=self.backend_name,
            is_output_active=False,
            error_message=error_message,
        )


def _clamp_position(position_sec: float, duration_sec: float | None) -> float:
    lower_bounded = max(0.0, float(position_sec))
    if duration_sec is None:
        return lower_bounded
    return min(lower_bounded, max(0.0, float(duration_sec)))
