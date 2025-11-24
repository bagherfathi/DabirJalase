# Desktop App Scaffold

This module bootstraps the JavaFX desktop shell for the Farsi meeting assistant. It mirrors the Product Build Blueprint with a focus on:

- **Audio capture + VAD + gRPC streaming** hooks.
- **Live chat UI** that prompts for unknown speakers and renders per-speaker quotes.
- **Local storage** with encrypted retention and migration stubs.
- **Diagnostics** for support bundles and offline smoke testing.

## Quickstart

1. Ensure Java 21+ and Maven are installed.
2. Build the scaffold (no external dependencies yet):
   ```bash
   mvn -f desktop-app/pom.xml clean compile
   ```
3. Extend the placeholders in `src/main/java/com/meetingassistant` with the platform-specific logic described in `docs/architecture.md`.

## Structure

- `app.Main` – entrypoint, config bootstrap, and JavaFX scene initialization.
- `audio.CaptureService` – audio line selection, buffering, and VAD hand-off.
- `audio.VadGate` – stub for silence detection to feed gRPC chunks.
- `transport.GrpcClient` – streaming hooks to the Python services.
- `ui.ChatTimeline` – RTL-friendly chat surface for per-speaker quotes.
- `ui.SpeakerPrompt` – prompts for unidentified speakers and stores responses.
- `storage.*` – SQLite DAO shell and migration notes for transcripts, embeddings, and policy tags.
- `security.*` – keystore and crypto helpers for at-rest encryption.
- `config.*` – feature flags and policy bundle selection.
- `diagnostics.*` – support bundle collector and smoke-test harness entrypoints.
- `tests/` – JUnit/TestFX slots for RTL screenshots and VAD/transport unit tests.

## Next steps

- Wire audio capture with platform defaults and basic VAD thresholding.
- Implement gRPC client with backpressure-aware streaming.
- Flesh out the chat UI with speaker prompts, confidence cues, and privacy curtain toggle.
- Add retention sweeper tasks and local keystore integration.
- Populate tests with the fixtures defined under `fixtures/` as they arrive.
