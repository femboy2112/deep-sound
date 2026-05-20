# FILE_PLAN — Living Build Backlog

**DO NOT HAND-EDIT THIS TABLE.** Use `python scripts/update_plan.py --id <id> --status <state>` to mutate rows. Direct edits are denied by `.claude/settings.json` (Claude Code) and discouraged for Codex.

The picker rule (encoded in `CLAUDE.md` and `AGENTS.md`):

> Lowest `id` row where `status == TODO`, every id in `depends_on` is `DONE`, and `phase <= ACTIVE_PHASE` (from `PHASES.md`).

Schema: `id` · `path` · `phase` · `spec_refs` · `status` · `depends_on` · `owner_agent` · `summary` · `verify` · `last_attempt` · `notes`.

## Rows

| id | path | phase | spec_refs | status | depends_on | owner_agent | summary | verify | last_attempt | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| P0-001 | pyproject.toml | 0 | §4 | DONE | - | build-engineer | uv-managed project, extras grouped by phase | `uv sync --extra dev` | 2026-05-15 | scaffolded |
| P0-002 | src/deep_sound/__init__.py | 0 | §4 | DONE | P0-001 | build-engineer | package init with __version__ | `python -c "import deep_sound"` | 2026-05-15 | scaffolded |
| P0-003 | src/deep_sound/domain/confidence.py | 0 | §3.3, §23.2 | DONE | P0-002 | build-engineer | Confidence value object with bands | `pytest tests/test_confidence_bands.py` | 2026-05-15 | scaffolded |
| P0-004 | src/deep_sound/domain/track.py | 0 | §11.2 | DONE | P0-002 | build-engineer | Track dataclass stub | `python -c "from deep_sound.domain.track import Track"` | 2026-05-15 | minimal stub |
| P0-005 | src/deep_sound/domain/stem.py | 0 | §11.2 | DONE | P0-002 | build-engineer | Stem dataclass stub | `python -c "from deep_sound.domain.stem import Stem"` | 2026-05-15 | minimal stub |
| P0-006 | src/deep_sound/domain/source.py | 0 | §11.2 | DONE | P0-002 | build-engineer | Source dataclass stub with source_type enum | `python -c "from deep_sound.domain.source import Source"` | 2026-05-15 | minimal stub |
| P0-007 | src/deep_sound/domain/feature_view.py | 0 | §11.2, §13.1 | DONE | P0-002 | build-engineer | FeatureView dataclass stub | `python -c "from deep_sound.domain.feature_view import FeatureView"` | 2026-05-15 | minimal stub |
| P0-008 | src/deep_sound/infra/analyzers/tempo_librosa.py | 0 | §13.2, §19 | DONE | P0-003 | build-engineer | librosa tempo+beats analyzer with confidence | `pytest tests/test_analyze.py` | 2026-05-15 | Phase 0 deliverable |
| P0-009 | src/deep_sound/cli.py | 0 | §19, §30 | DONE | P0-008 | build-engineer | click CLI with `analyze` subcommand | `pytest tests/test_cli.py tests/test_analyze.py` | 2026-05-15 | scaffolded |
| P0-010 | tests/conftest.py | 0 | §21.3 | DONE | P0-001 | build-engineer | pytest fixtures incl. click_track_wav | `pytest --collect-only` | 2026-05-15 | scaffolded |
| P0-011 | tests/test_cli.py | 0 | §19 | DONE | P0-009 | build-engineer | --help smoke test | `pytest tests/test_cli.py` | 2026-05-15 | scaffolded |
| P0-012 | tests/test_analyze.py | 0 | §13.2 | DONE | P0-008,P0-009,P0-010 | build-engineer | analyze CLI on click-track returns tempo | `pytest tests/test_analyze.py` | 2026-05-15 | scaffolded |
| P0-013 | tests/test_confidence_bands.py | 0 | §23.2 | DONE | P0-003 | build-engineer | Confidence band boundary tests | `pytest tests/test_confidence_bands.py` | 2026-05-15 | scaffolded |
| P0-014 | src/deep_sound/infra/analyzers/chroma_librosa.py | 0 | §13.4, §19 | TODO | P0-008 | build-engineer | librosa chroma feature (track-level summary) | `pytest tests/test_chroma.py` | - | needs new test file |
| P0-015 | src/deep_sound/infra/analyzers/mfcc_librosa.py | 0 | §13.7, §19 | TODO | P0-008 | build-engineer | librosa MFCC summary stats (timbre) | `pytest tests/test_mfcc.py` | - | needs new test file |
| P0-016 | src/deep_sound/services/feature_service.py | 0 | §10.2, §16.4 | TODO | P0-007 | build-engineer | minimal in-memory FeatureService for Phase 0 | `pytest tests/test_feature_service.py` | - | upgrade to SQLite in P1 |
| P0-017 | src/deep_sound/services/similarity_service.py | 0 | §10.2, §14.1, §14.2 | TODO | P0-016 | build-engineer | weighted cosine similarity over feature vectors | `pytest tests/test_similarity.py` | - | FAISS deferred to P1 |
| P0-018 | src/deep_sound/cli.py (extend) | 0 | §19 | TODO | P0-017 | build-engineer | add `search-similar` subcommand with --mode rhythm/harmony/timbre/weighted | `pytest tests/test_search_cli.py` | - | spec §19 deliverable |
| P0-019 | tests/test_chroma.py | 0 | §13.4 | TODO | P0-014 | build-engineer | chroma analyzer returns 12-d vector | `pytest tests/test_chroma.py` | - | - |
| P0-020 | tests/test_mfcc.py | 0 | §13.7 | TODO | P0-015 | build-engineer | MFCC analyzer returns summary stats | `pytest tests/test_mfcc.py` | - | - |
| P0-021 | tests/test_feature_service.py | 0 | §16.4 | TODO | P0-016 | build-engineer | FeatureService get/put round-trip | `pytest tests/test_feature_service.py` | - | - |
| P0-022 | tests/test_similarity.py | 0 | §14.1, §14.2 | TODO | P0-017 | build-engineer | weighted cosine ranks by similarity | `pytest tests/test_similarity.py` | - | - |
| P0-023 | tests/test_search_cli.py | 0 | §19 | TODO | P0-018 | build-engineer | search-similar CLI end-to-end | `pytest tests/test_search_cli.py` | - | - |
| P1-001 | src/deep_sound/infra/storage/sqlite_store.py | 1 | §11.2, §17.1 | TODO | P0-004,P0-005,P0-006,P0-007 | build-engineer | SQLite schema + DAOs for tracks/sections/stems/sources/feature_views | `pytest tests/test_sqlite_store.py` | - | core P1 infra |
| P1-002 | src/deep_sound/services/library_service.py | 1 | §10.2, §16.1, §8.1 | TODO | P1-001 | build-engineer | LibraryService: import files/folders, metadata extract, dedupe by hash | `pytest tests/test_library_service.py` | - | - |
| P1-003 | src/deep_sound/services/analysis_service.py | 1 | §10.2, §16.2 | TODO | P1-001,P0-017 | build-engineer | AnalysisService orchestrating extractors; emits progress | `pytest tests/test_analysis_service.py` | - | - |
| P1-004 | src/deep_sound/infra/job_queue.py | 1 | §10.3, §NFR-001,§NFR-003 | TODO | - | build-engineer | background job queue (multiprocessing); UI never blocked | `pytest tests/test_job_queue.py` | - | - |
| P1-005 | src/deep_sound/infra/index/faiss_index.py | 1 | §14.3, §17.1 | TODO | P0-017 | build-engineer | FAISS-backed vector index with manifest | `pytest tests/test_faiss_index.py` | - | - |
| P1-006 | src/deep_sound/ui/main_window.py | 1 | §15.1, §15.2 | TODO | P1-002,P1-003 | build-engineer | PySide6 main window with library view | manual smoke test | - | needs `--extra ui` |
| P1-007 | src/deep_sound/ui/track_detail.py | 1 | §15.3 | TODO | P1-006 | build-engineer | PySide6 track detail with waveform + sections | manual smoke test | - | - |
| P1-008 | src/deep_sound/ui/query_builder.py | 1 | §15.5 | TODO | P1-006 | build-engineer | PySide6 query builder with weighted sliders | manual smoke test | - | - |
| P1-009 | src/deep_sound/ui/results_view.py | 1 | §15.6, §14.8 | TODO | P1-006,P1-005 | build-engineer | PySide6 result cards with per-dimension scores | manual smoke test | - | - |
| P1-010 | src/deep_sound/services/explanation_service.py | 1 | §10.2, §16.6, §14.8 | TODO | P1-005 | build-engineer | converts ScoreDetails → human-readable summary | `pytest tests/test_explanation_service.py` | - | - |
