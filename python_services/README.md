# Python Services Scaffold

Lightweight FastAPI-based services for transcription, diarization, TTS, and summarization. Implementations are deterministic stubs so the scaffold runs without heavy model downloads; swap in real models and adapters when wiring the MVP slice.

## Endpoints
- `GET /health` — readiness probe
- `POST /transcribe` — accepts `{ content, language }`, returns transcript segments
- `POST /diarize` — accepts `{ transcript }`, returns hashed speaker labels
- `POST /summarize` — accepts `{ transcript, max_points }`, returns bullet points and a highlight
- `POST /tts` — accepts `{ text, voice }`, returns base64-encoded payload

## Local development
1. Create a virtualenv and install dependencies from `requirements.txt` (model extras can remain commented out in constrained environments).
2. Run the API with `uvicorn python_services.api.server:app --reload`.
3. Exercise the scaffold with `curl` or a REST client; responses are deterministic for easy testing.

## Next steps
- Replace stub services with real Whisper/pyannote/Coqui adapters and cache layers.
- Add authz/authn middleware, gRPC streaming, and structured logging per the architecture.
- Introduce golden fixtures and regression tests that validate WER, DER, and summary faithfulness.
