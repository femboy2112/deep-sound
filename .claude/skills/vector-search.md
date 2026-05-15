---
name: vector-search
description: Patterns for similarity search — candidate retrieval, reranking, FAISS indices. Triggers on "faiss", "index", "embedding similarity", "candidate retrieval", "rerank", "vector search", "knn", "cosine similarity". Use when implementing similarity_service or faiss_index.
---

# Vector search patterns

Authoritative source: spec §14 (similarity search).

## Two-stage retrieval (spec §14.3, §14.4)

```
1. Extract or load query feature views.
2. For each selected feature_type, search its vector index → top K per feature.
3. Merge candidates by entity id.
4. Rerank with slower, more musically meaningful methods.
```

Recommended top-K per feature (spec §14.3):

| Library size | Top K |
|---|---|
| < 5,000 segments | 100 |
| 5k–100k segments | 200–500 |
| > 100k segments | 500+ with approximate index tuning |

## Reranking methods (spec §14.4)

| Dimension | Reranking |
|---|---|
| Rhythm | DTW over beat-synchronous onset vectors |
| Chords | Edit distance over roman numeral tokens |
| Chord changes | Alignment over timing + root-movement events |
| Bass | Contour alignment + root interval comparison |
| Timbre | Cosine or learned metric on embeddings |
| Structure | Section sequence alignment |
| Source behavior | Source-type constrained comparison |

## Weighted scoring (spec §14.1)

```
combined_score = sum(weight_i * score_i) / sum(weight_i)
```

Every per-dimension score normalized to `[0, 1]`.

## Transposition invariance (spec §14.5)

For harmony searches, compare roman numerals (or normalize chord roots) so `C → G → Am → F` matches `D → A → Bm → G` (both `I → V → vi → IV`).

## Tempo invariance (spec §14.6)

User toggle:
```
[ ] Match exact tempo
[x] Allow tempo-scaled rhythm similarity
[x] Compare beat-relative groove
```

## Source-constrained matching (spec §14.7)

When the query selects a source, candidates filtered by compatible `source_type`. Drums excluded from chord searches by default.

## FAISS idioms

```python
import faiss
index = faiss.IndexFlatIP(dim)        # exact inner product
# or for scale:
quantizer = faiss.IndexFlatL2(dim)
index = faiss.IndexIVFFlat(quantizer, dim, nlist=100)
index.train(vectors)
index.add(vectors)
D, I = index.search(query, k)
```

A manifest file maps each vector row → entity id.

## Explanation (spec §14.8)

Every result returns: combined score, per-dimension scores, matched entity (track/section/source/clip), matched time range, confidence indicators, human-readable summary.
