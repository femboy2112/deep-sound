"""AudioDecoder — convert input audio to normalized PCM. Spec §12.2."""

from __future__ import annotations

from pathlib import Path


class AudioDecoder:
    """Decode supported audio formats to internal PCM (analysis copy only).

    Spec §12.2: original file is never modified. Resample to a configured
    analysis sample rate; optionally create mono and stereo copies.

    Stub — implemented in Phase 1.
    """

    def decode(self, path: Path, sample_rate: int = 22050) -> object:  # returns ndarray
        raise NotImplementedError("AudioDecoder.decode pending Phase 1")
