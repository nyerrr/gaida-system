# Gaida Backend

> ⚠️ **Pending database migrations — not yet confirmed against production.**
> See [`../HANDOFF.md`](../HANDOFF.md) §1: three steps, about five minutes.

## Audio Processing Libraries

This backend now includes the following audio processing libraries:

- **Librosa** (0.11.0) - Audio analysis and feature extraction
- **OpenSMILE** (2.6.0) - Audio feature extraction toolkit
- **PyAudio** (0.2.14) - Audio I/O library
- **SpeechRecognition** (3.14.5) - Speech-to-text conversion

## Run:

> uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
