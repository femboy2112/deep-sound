---
name: mir-confidence-policy
description: Enforces the project-wide confidence policy from spec §3.3 and §23. Triggers on "confidence", "infer", "infer label", "likely", "probabilistic", "estimate", "uncertainty". Apply whenever code emits a label, chord, source, section, or event.
---

# Confidence policy

Authoritative source: spec §3.3, §23.

## The rule

**Every inferred label, source, chord, section, or event MUST carry a `confidence` in `[0, 1]`.** No exceptions, no bare floats labeled "confidence", no `Optional[float]` for fields that the spec marks as mandatory.

Use the type:

```python
from deep_sound.domain.confidence import Confidence, ConfidenceBand

c = Confidence(0.74)
assert 0.0 <= c.value <= 1.0
assert c.band is ConfidenceBand.MEDIUM
```

The `Confidence` value object:
- clamps values to `[0, 1]` (no surprise crashes on `1.5` or `-0.3`),
- rejects `NaN`,
- exposes a `.band` for UI display.

## Bands (spec §23.2)

| Range | Band | Default visibility |
|---|---|---|
| 0.80–1.00 | HIGH | shown |
| 0.60–0.79 | MEDIUM | shown |
| 0.40–0.59 | LOW | shown |
| < 0.40 | VERY_UNCERTAIN | hidden unless diagnostics enabled |

## Forbidden phrases

- "This is definitely a Guitar playing Am7." ❌
- "Detected: Am7." ❌ (missing confidence)
- Returning a label without its confidence as a sibling field. ❌

## Required phrasing

- "Detected source: likely electric guitar (confidence 0.78)." ✅
- "Chord event: likely Am7 (confidence 0.64)." ✅

## How this flows through the data model

- `Stem.confidence: Confidence`
- `Source.confidence: Confidence`
- `FeatureView.confidence: Confidence | None` (None means "this kind of view doesn't have one", e.g. raw MFCC stats — but every *label* still does)
- `ChordEvent.confidence: float` in the SQLite schema, but constructed from a `Confidence` in code.
- `Section.confidence: float` similarly.

## Test invariant

If a `domain` field is `Confidence`, the corresponding test should exercise at least one boundary (0.0, 0.4, 0.6, 0.8, 1.0) so the band logic stays correct.
