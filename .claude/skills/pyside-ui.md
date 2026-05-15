---
name: pyside-ui
description: Patterns for the PySide6 desktop UI. Triggers on "qt", "pyside", "pyside6", "main window", "widget", "waveform", "ui thread", "library view", "track detail". Use when implementing anything under src/deep_sound/ui.
---

# PySide6 / Qt patterns

Authoritative source: spec §15 (UI), §10.3 (processing boundary).

## UI threading rule — HARD (spec §10.3, NFR-001)

The UI thread NEVER runs analysis. Decode, separation, feature extraction, index build, search rerank: all happen in worker processes via the Job Queue (spec §10.3).

Use `QThreadPool` for short tasks, `multiprocessing` for CPU-heavy jobs (librosa, demucs). Communicate results via Qt signals.

## Required views (spec §15.1)

| View | Purpose |
|---|---|
| Library View | Import, browse, filter, analysis status |
| Track Detail | Waveform, playback, sections, sources, features |
| Source Graph | Tree of stems and detected sources |
| Query Builder | Source/clip selection + weighted similarity sliders |
| Results View | Ranked matches with per-dimension scores |
| Analysis Queue | Job progress / failures |
| Corrections | User overrides |
| Settings | Models, paths, cache, privacy |

## Result cards (spec §15.6)

Every result card includes:
- track title + artist
- matched time range
- matched source (if applicable)
- combined score
- per-dimension scores
- confidence warnings
- play preview · compare · mark relevant/irrelevant

## Confidence visualization (spec §23.2)

Use bands from `deep_sound.domain.confidence.ConfidenceBand`. Very-uncertain claims hidden by default unless the user toggles diagnostics.

## Skeleton

```python
from PySide6.QtWidgets import QApplication, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("deep-sound")
        # ...

def main() -> None:
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
```

## Don't

- Don't run librosa / demucs in the UI thread.
- Don't block the event loop on disk I/O. Use `QFileSystemModel` or worker threads.
- Don't pickle huge ndarrays through Qt signals; pass file paths instead.
- Don't add PySide6 imports outside `src/deep_sound/ui/` — keep the UI optional.
