# Test fixtures

This directory exists for committed binary fixtures (none yet).

Audio fixtures used by the test suite are **generated at runtime** by
`tests/conftest.py` into a `tmp_path` so we never commit WAV/MP3 files.

The default fixture is a 120-BPM **click track** (impulses every 0.5 s, not a
pure sine) so `librosa.beat.beat_track` actually has onsets to lock to.
A pure sine would return `tempo=0`.
