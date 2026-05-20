# Phase 9 Plan — Interactive Desktop Beta Hardening

Phase 9 is the next stage after the completed Phase 8 import-safe desktop workflow seam. It should not begin until `ACTIVE_PHASE` is promoted to 9.

The first constraint is acceptance hardening: prove the Phase 8 controller, CLI/service parity, stale-state disclosure, artifact safety, and probabilistic result language across realistic local workflows before depending on richer interactive UI behavior.

## Priority Order

1. **High priority / high effort:** End-to-end controller and CLI/service parity acceptance tests for import, analyze, index, search, waveform, clip selection, feedback, and snapshots.
2. **High priority / high effort:** PySide application bootstrap, main-window signal wiring, and background runner integration.
3. **High priority / high effort:** Track detail waveform panel integration and clip-owned feature materialization before clip search.
4. **Medium-high priority:** Query builder, result feedback actions, source graph/detail interaction wiring, stale-index/correction regression coverage, and result disclosure checks.
5. **Medium priority:** Optional PySide smoke tests, manual QA refresh, audit refresh, and closeout verification.

## Skill And Tool Use

- Use `deep-sound-build-loop` for status, picker discipline, verification, and closeout.
- Use `pyside-ui` for all PySide factories, signal/slot wiring, widget state, and UI-thread safety.
- Use `audio-pipeline` for background analysis, waveform, and clip feature materialization.
- Use `vector-search` for query state, clip/source search mode mapping, result metadata, and stale-index disclosure.
- Use `source-separation` for source graph/detail controls and fake-provider source-aware boundaries.
- Use `mir-confidence-policy` for all user-facing source, chord, event, and match wording.
- Use `harness-maintenance` for PHASES, README, REPO_AUDIT, manual QA, and build-log updates.
- Use `harness-self-review` at closeout through `python3 scripts/toolset_review.py`.

## Parallelization Plan

Start with read-only explorers:

- Explorer A, high effort: inspect PySide app/window factories and propose concrete signal/slot wiring.
- Explorer B, high effort: inspect controller/job semantics and propose the background runner contract.
- Explorer C, medium effort: inspect clip storage/analyzer paths and propose clip-owned feature materialization.
- Explorer D, medium effort: inspect result/source/query DTOs and propose widget callback contracts.
- Explorer E, medium effort: inspect acceptance coverage gaps for CLI/controller parity, stale-index regressions, artifact safety, and optional dependency boundaries.

Then split implementation with disjoint ownership:

- Worker A owns `src/deep_sound/ui/desktop_app.py` and bootstrap tests.
- Worker B owns `src/deep_sound/ui/background_runner.py` and job progress tests.
- Worker C owns `src/deep_sound/ui/main_window.py` wiring.
- Worker D owns `src/deep_sound/ui/track_detail.py` and waveform/clip integration.
- Worker E owns `src/deep_sound/services/clip_analysis_service.py`.
- Worker F owns query/result/source widget callback DTOs.
- Worker G owns docs/manual QA/audit closeout.
- Worker H owns acceptance-only tests for controller E2E, CLI parity, stale-index/correction disclosure, and original-audio/artifact safety.

Avoid concurrent edits to the same UI module. Run verifier checks in parallel with non-overlapping implementation whenever possible.

## Verification

- Keep default `python3 scripts/verify.py` green without PySide, FAISS, Demucs, or heavy MIR extras.
- Add optional PySide smoke tests with `pytest.importorskip("PySide6")`.
- Cover controller/CLI parity, idempotency, stale-index fallback, feedback adjustment disclosure, and app-data artifact placement with dependency-light tests.
- Run focused Phase 9 tests after each implementation slice.
- Final gate: `python3 scripts/verify.py`, `python3 scripts/status.py`, and `python3 scripts/toolset_review.py`.
