"""Import-safe waveform and clip panel DTOs for desktop beta."""

from __future__ import annotations

from dataclasses import dataclass

from deep_sound.services.waveform_service import ClipWindowDTO, WaveformCacheDTO


@dataclass(frozen=True, slots=True)
class WaveformRenderPoint:
    x_start: float
    x_end: float
    y_min: float
    y_max: float
    rms: float


@dataclass(frozen=True, slots=True)
class ClipSelectionState:
    track_id: str
    start_sec: float
    end_sec: float
    label: str | None = None
    persisted_clip_id: str | None = None


@dataclass(frozen=True, slots=True)
class WaveformPanelData:
    track_id: str
    duration_sec: float
    cache_version: str
    render_points: tuple[WaveformRenderPoint, ...]
    selected_clip: ClipSelectionState | None = None
    persisted_clips: tuple[ClipWindowDTO, ...] = ()


def waveform_panel_data(
    cache: WaveformCacheDTO,
    *,
    selected_clip: ClipSelectionState | None = None,
    persisted_clips: tuple[ClipWindowDTO, ...] = (),
) -> WaveformPanelData:
    duration = max(cache.duration_sec, 0.000001)
    return WaveformPanelData(
        track_id=cache.track_id,
        duration_sec=cache.duration_sec,
        cache_version=cache.version,
        render_points=tuple(
            WaveformRenderPoint(
                x_start=point.start_sec / duration,
                x_end=point.end_sec / duration,
                y_min=max(-1.0, min(1.0, point.min_amplitude)),
                y_max=max(-1.0, min(1.0, point.max_amplitude)),
                rms=max(0.0, min(1.0, point.rms)),
            )
            for point in cache.points
        ),
        selected_clip=selected_clip,
        persisted_clips=persisted_clips,
    )


def create_waveform_panel(data: WaveformPanelData) -> object:
    """Create a simple PySide waveform panel from import-safe DTOs."""
    try:
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.addWidget(
        QLabel(
            f"Waveform {data.track_id}  {data.duration_sec:.2f}s  {len(data.render_points)} points"
        )
    )
    if data.selected_clip is not None:
        clip = data.selected_clip
        layout.addWidget(QLabel(f"Selected clip {clip.start_sec:.2f}-{clip.end_sec:.2f}s"))
    for persisted_clip in data.persisted_clips:
        label = persisted_clip.label or "clip"
        layout.addWidget(
            QLabel(f"{label}: {persisted_clip.start_sec:.2f}-{persisted_clip.end_sec:.2f}s")
        )
    return root
