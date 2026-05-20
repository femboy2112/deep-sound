---
name: vector-search
description: Use when implementing similarity scoring, candidate retrieval, reranking, weighted scoring, FAISS integration, or index manifests in Deep-Sound.
---

# Vector Search

Use this skill for `similarity_service`, `faiss_index`, and search-facing CLI or UI work.

## Core rules

- Keep per-dimension scores normalized to `[0, 1]`.
- Treat retrieval and reranking as separate stages.
- Preserve source-type compatibility filters.
- Keep explanations aligned with per-dimension scoring.

## Read next when needed

- `docs/SPEC.md` section 14
- `docs/PIPELINE.md`
- `docs/ARCHITECTURE.md`

