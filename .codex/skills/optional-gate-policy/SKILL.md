---
name: optional-gate-policy
description: Use when touching Deep-Sound optional extras, live QA policies, Demucs, PySide, playback, uv.lock, or dependency-light verification boundaries.
---

# Optional Gate Policy

Use this skill before editing optional dependency surfaces or smoke gates.

## Surfaces

- `pyproject.toml`
- `uv.lock`
- `scripts/live_qa.py`
- `src/deep_sound/infra/separation/providers.py`
- `src/deep_sound/services/playback_service.py`
- `src/deep_sound/ui/*`
- `tests/test_phase12_optional_extra_resolution.py`
- `tests/test_phase12_live_qa_policy.py`
- `tests/test_phase13_live_qa_playback_policy.py`

## Rules

- Default verification must not require Demucs, PySide, FAISS, playback devices, learned models, cloud services, or GPU packages.
- Real smoke policies use `auto|required|off`.
- `auto` records skipped optional gates when dependencies are absent.
- `required` turns missing or failing optional gates into failures.
- `off` records an explicit skip even when run flags are supplied.
- Keep Torch/Torchaudio on the explicit `pytorch-cpu` uv index for the `[demucs]` extra.
- Keep `torchcodec` in `[demucs]` unless a later real-smoke test proves it is unnecessary.
- Do not add CUDA, NVIDIA, or Triton packages to the default CPU Demucs path.
