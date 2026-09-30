# Gaida Backend

> ⚠️ **Pending database migrations — not yet confirmed against production.**
> See [`../HANDOFF.md`](../HANDOFF.md) §1: three steps, about five minutes.

## Audio Processing Libraries

This backend now includes the following audio processing libraries:

- **Librosa** (0.11.0) - Audio analysis and feature extraction
- **NoiseReduce** (3.0.3) - Background-noise removal (stationary spectral gating)
- **OpenSMILE** (2.6.0) - Audio feature extraction toolkit
- **PyAudio** (0.2.14) - Audio I/O library
- **SpeechRecognition** (3.14.5) - Speech-to-text conversion

## Voice Cleaning

Before acoustic feature extraction, every recording is cleaned in
`app/analytics/voice_cleaning.py`:

1. **Denoise** — stationary spectral gating (`noisereduce`), conservative
   `prop_decrease=0.75`. The noise profile is taken from the recording's
   quiet lead-in when one exists (typical of browser-mic recordings), else
   noisereduce falls back to whole-clip statistics.
2. **Normalize** — RMS-normalized to a fixed target (0.05) so energy-based
   comparisons are fair across mics/volumes.

Tunables (all optional): `GAIDA_VOICE_CLEANING`, `GAIDA_NOISE_PROP_DECREASE`,
`GAIDA_NOISE_N_STD_THRESH`, `GAIDA_VOICE_NORM_TARGET_RMS`. Set
`GAIDA_VOICE_CLEANING=0` to disable and restore the raw pipeline bit-for-bit.

A/B comparison tool: `python tools/validate_voice_cleaning.py [clip.wav]`

## Run:

> uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
