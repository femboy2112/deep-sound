---
name: mir-confidence-policy
description: Use when code or docs emit inferred labels, events, sources, chords, or uncertainty-bearing results in Deep-Sound.
---

# MIR Confidence Policy

Every inferred label or event must be probabilistic.

## Required behavior

- Use `deep_sound.domain.confidence.Confidence` in code.
- Keep values within `[0, 1]`.
- Avoid definitive phrasing in docs and CLI output.
- Preserve confidence-band semantics from `docs/DATA_MODEL.md`.

## Trigger areas

- analyzers
- sources
- chord or section inference
- result explanations
- user-facing summaries

