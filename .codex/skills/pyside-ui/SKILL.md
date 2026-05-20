---
name: pyside-ui
description: Use when implementing or reviewing PySide6 UI code, widget boundaries, result views, or UI-thread safety in Deep-Sound.
---

# PySide UI

Use this skill for future work under `src/deep_sound/ui/`.

## Core rules

- Do not run analysis work in the UI thread.
- Keep PySide imports inside UI-focused modules.
- Preserve required result-card fields and confidence visibility.
- Treat Phase 1 as the first UI-capable phase.

## Read next when needed

- `docs/SPEC.md` section 15
- `docs/ARCHITECTURE.md`

