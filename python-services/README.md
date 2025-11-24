# Python Services Scaffold

This directory seeds the service-side components described in the Product Build Blueprint:

- **`stt/`** – Whisper primary + Vosk fallback wrappers, fixtures, and WER harness hooks.
- **`diarization/`** – pyannote pipeline shell with spoof checks and gallery refresh jobs.
- **`tts/`** – Azure/Google/Coqui adapters with caching and pronunciation normalization.
- **`summarization/`** – LLM wrappers with faithfulness/citation tracing.
- **`api/`** – gRPC/REST endpoints that front the audio pipeline with auth hooks.
- **`storage/`** – embedding/manifests helpers; plug in Postgres or local disk.
- **`ops/`** – metrics, health endpoints, and configuration validation.
- **`tests/`** – PyTest harness tied to the fixtures and quality gates.
- **`scripts/`** – model download and signature verification utilities.

## Quickstart

1. Create a virtual environment and install the (placeholder) requirements:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Flesh out the service modules before exposing the gRPC interface described in `docs/architecture.md`.
3. Add fixtures under `fixtures/` and wire the harness scripts to enforce WER/DER/summary thresholds.
