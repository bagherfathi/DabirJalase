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
- `POST /sessions/{id}/speakers/forget` — redact a speaker’s text and clear their display name (privacy/DSR helper)
- `GET /sessions/{id}` — fetch timeline segments with speaker labels where available
- `GET /sessions/{id}/summary` — summarize accumulated segments for the session
- `GET /sessions/{id}/export` — export the full meeting manifest with speaker labels and a deterministic summary for download or archival
- `POST /sessions/{id}/export/store` — export and persist the manifest to `PY_SERVICES_STORAGE_DIR` (defaults to `./data/exports`)
- `DELETE /sessions/{id}` — remove the in-memory session and any persisted export manifest (idempotent)
- `POST /exports/retention/sweep` — prune stored manifests older than the configured retention window (if enabled)

Speaker redaction + session deletion endpoints exist to mirror privacy/DSR flows before the full auth stack and forget-speaker pipeline land.
- `GET /exports` — list stored export ids; `GET /exports/{id}` — fetch a stored export from disk
- `POST /exports/retention/sweep` — delete stored exports older than the retention window (configured via env or request body)

Replace these with durable storage/queue-backed flows when wiring the production pipeline.

### Demo harness

- Run a deterministic end-to-end flow (create session → diarize → label speakers → summarize → export) without hitting the API via `python -m python_services.scripts.demo_session`. Add `--persist ./data/exports` to write the manifest to disk for inspection.

### In-process smoke test

- Validate the stitched API without running a server by executing `python -m python_services.ops.smoke`. The harness exercises session creation, diarization, speaker labeling, summary, export, persistence, and retrieval. Override with `--api-key` or `--storage-dir` to mirror deployment settings.

### Access control and traceability

- Requests include an `x-request-id` header (configurable via `PY_SERVICES_REQUEST_ID_HEADER`) so clients can correlate logs and responses.
- Set `PY_SERVICES_API_KEY` to enforce a static API key; requests without the correct `x-api-key` will receive `401` responses so the scaffold can be exercised behind a gateway or tunnel.
- Set `PY_SERVICES_ALLOWED_ORIGINS` (comma-separated) to emit CORS headers for browser clients; defaults to `*`.
- Set `PY_SERVICES_MAX_REQUESTS_PER_MINUTE` to add simple in-memory rate limiting that returns `429` when exceeded.
- Set `PY_SERVICES_STORAGE_DIR` to change where export manifests are written when using `/sessions/{id}/export/store`.
- Configure `PY_SERVICES_EXPORT_RETENTION_DAYS` (default: `30`) to prune exports automatically after `/sessions/{id}/export/store` calls; set to `none` to disable automatic pruning and rely on `/exports/retention/sweep` instead.

## Local development
1. Create a virtualenv and install dependencies from `requirements.txt` (model extras can remain commented out in constrained environments).
2. Run the API with `python -m python_services` (or override defaults with `PY_SERVICES_HOST`, `PY_SERVICES_PORT`, `PY_SERVICES_RELOAD`, `PY_SERVICES_LOG_LEVEL`, `PY_SERVICES_STORAGE_DIR`, `PY_SERVICES_EXPORT_RETENTION_DAYS`, `PY_SERVICES_ALLOWED_ORIGINS`, `PY_SERVICES_MAX_REQUESTS_PER_MINUTE`).
3. Exercise the scaffold with `curl` or a REST client; responses are deterministic for easy testing.

### Containerized scaffold
- Build the lean image (uvicorn only; uses local FastAPI/Pydantic shims) with `docker build -f python_services/Dockerfile -t meeting-assistant-services .`.
- Run the container with `docker run -p 8000:8000 -e PY_SERVICES_EXPORT_RETENTION_DAYS=30 meeting-assistant-services` to expose the API locally.

## Next steps
- Replace stub services with real Whisper/pyannote/Coqui adapters and cache layers.
- Add authz/authn middleware, gRPC streaming, and structured logging per the architecture.
- Introduce golden fixtures and regression tests that validate WER, DER, and summary faithfulness.
