# Delivery Status Snapshot

## Backend (python_services)
- **Current readiness:** Scaffolded and runnable offline via `python -m python_services` or the lean Dockerfile; exposes deterministic REST endpoints for transcription, diarization, summarization, TTS, session orchestration, exports, privacy hooks, and optional API key/rate-limit/CORS middleware.
- **Pending for MVP:** Replace deterministic stubs with production STT/TTS/diarization models (Whisper/pyannote), wire gRPC streaming inputs, storage beyond in-memory/disk manifests, and end-to-end authN/Z.

## Windows frontend (desktop-app)
- **Current readiness:** JavaFX shell with placeholders for capture, VAD gating, gRPC client, UI timeline/prompts, storage, security, diagnostics, and feature flags; compiles outside the sandbox when Maven Central is reachable.
- **Pending for MVP:** Implement audio capture/VAD, live streaming to Python services, speaker prompt loop, summary export, and installer smoke tests with quality gates.

## Priority guidance for MVP
1. **Base capture + streaming + STT/diarization path** (unblock end-to-end transcript with speaker prompts).
2. **Summary/export flow and data retention/privacy basics.**
3. **TTS/playback and UX polish (RTL, accessibility).**
4. **Operational gates (fixtures, readiness checks) and installers.**
5. **Defensive controls** like rate limiting/CORS are useful for deployment but should not block the core MVP pipeline above.
