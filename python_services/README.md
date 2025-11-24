# Python Services Scaffold

Lightweight FastAPI-based services for transcription, diarization, TTS, and summarization. Implementations are deterministic stubs so the scaffold runs without heavy model downloads; swap in real models and adapters when wiring the MVP slice.

## Endpoints
- `GET /health` — readiness probe
- `POST /transcribe` — accepts `{ content, language }`, returns transcript segments
- `POST /diarize` — accepts `{ transcript }`, returns hashed speaker labels
- `POST /summarize` — accepts `{ transcript, max_points }`, returns bullet points and a highlight
- `POST /tts` — accepts `{ text, voice }`, returns base64-encoded payload

### Session flow

To keep the scaffold product-shaped, a minimal in-memory session orchestrator stitches the stubs together:

- `POST /sessions` — create a session id and language
- `POST /sessions/append` — run placeholder STT + diarization and append segments to the session, returning any newly seen speakers
- `POST /sessions/{id}/speakers` — label an unlabeled speaker id with a friendly name (for "who is this?" prompts)
- `GET /sessions/{id}` — fetch timeline segments with speaker labels where available
- `GET /sessions/{id}/summary` — summarize accumulated segments for the session

Replace these with durable storage/queue-backed flows when wiring the production pipeline.

## Local development
1. Create a virtualenv and install dependencies from `requirements.txt` (model extras can remain commented out in constrained environments).
2. Run the API with `python -m python_services` (or override defaults with `PY_SERVICES_HOST`, `PY_SERVICES_PORT`, `PY_SERVICES_RELOAD`, `PY_SERVICES_LOG_LEVEL`).
3. Exercise the scaffold with `curl` or a REST client; responses are deterministic for easy testing.

## Next steps
- Replace stub services with real Whisper/pyannote/Coqui adapters and cache layers.
- Add authz/authn middleware, gRPC streaming, and structured logging per the architecture.
- Introduce golden fixtures and regression tests that validate WER, DER, and summary faithfulness.
