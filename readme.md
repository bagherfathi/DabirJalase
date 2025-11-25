# Meeting Transcriber – Project Blueprint

This repository contains a blueprint for a cross-platform meeting-transcription assistant focused on high-quality Farsi speech processing. The design favors a shared Kotlin/Java core so Android and desktop targets can reuse audio, STT/TTS, and summarization pipelines while keeping UI layers platform-specific.

## Goals
- **Cross-platform:** Android and desktop (JavaFX or Compose Multiplatform for desktop) sharing the same core audio pipeline.
- **High-quality Farsi STT:** Whisper large-v3 (or comparable) via ONNX Runtime for local inference; fallback to cloud APIs when available.
- **High-quality Farsi TTS:** Coqui TTS or Microsoft Azure Neural Farsi voices with pluggable provider interface.
- **Speaker identification:** PyAnnote-like diarization models converted to ONNX, cached embeddings, and user prompts for unknown speakers.
- **Automatic silence detection:** Silero VAD/voice activity detection (ONNX) to segment audio and trigger STT quickly.
- **Conversational view:** Ask “who is this?” when a new speaker is detected, then render their quotations in a chat-style timeline tagged with their name.
- **Meeting summaries:** Build structured summaries and bullet point exports (Markdown/JSON) using local LLMs (e.g., Llama 3 Instruct) or remote services.
- **Noise robustness:** Beamforming/noise suppression (RNNoise/NSNet2) and energy-based focus on the active speaker.

## Proposed Architecture
- **Shared Core (Kotlin/Java):**
  - Audio capture/streaming using Oboe (Android) and Java Sound (desktop).
  - VAD module (Silero) for chunking and silence-based flushing to STT.
  - STT module with interchangeable engines (Whisper ONNX, cloud API).
  - Speaker diarization/ID module with embedding cache and enrollment prompts.
  - TTS module with provider abstraction and prosody controls.
  - Conversation state manager to pair speaker labels with utterances and trigger prompts for unknown voices.
  - Summarization service that ingests the conversation log and outputs concise highlights.
- **Platform UI layers:**
  - **Android:** Compose UI; permission handling, foreground service for continuous recording, and notifications when summarization completes.
  - **Desktop:** Compose Multiplatform or JavaFX; displays waveform, live transcripts, speaker cards, and export buttons.

## Data Flow
1. **Capture:** Microphone stream passes through RNNoise/NSNet2 for denoising.
2. **VAD:** Silero segments audio; on speech end, the buffered chunk is dispatched to STT.
3. **STT:** Whisper ONNX transcribes Farsi audio with timestamps.
4. **Diarization & ID:** PyAnnote-style diarization marks speakers; if embedding not recognized, UI asks “who is this?” and stores the label.
5. **Conversation View:** UI renders chat bubbles labeled with speaker name; messages are stored for summarization.
6. **Summarization:** LLM generates bullet points and action items; export to Markdown/JSON.
7. **TTS:** Selected utterances can be spoken back in Farsi using TTS provider.

## Key Modules to Implement
- `core/audio`: Capture, denoise, VAD, buffering, and silence-based dispatch.
- `core/stt`: Whisper ONNX runner with streaming and batching; adapters for cloud STT.
- `core/diarization`: Speaker change detection, embedding store, and enrollment prompts.
- `core/tts`: Provider abstraction with configurable voices and speaking style.
- `core/summarization`: Prompt templates for meeting notes; local/remote LLM runners.
- `ui/chat`: Timeline that attaches names to quotes; “who is this?” prompt handler.
- `ui/export`: Markdown/JSON writer for summaries and full transcripts.

## Pipeline Pseudocode
```kotlin
val vad = SileroVad()
val stt = WhisperOnnx(modelPath)
val diarizer = SpeakerIdEngine(embeddingStore)
val convo = ConversationState()

microphone.stream().pipe(NoiseSuppressor()).onChunk { frames ->
    if (vad.isSpeech(frames)) {
        buffer.add(frames)
    } else if (buffer.isNotEmpty()) {
        val audioChunk = buffer.flush()
        val transcript = stt.transcribe(audioChunk)
        val speaker = diarizer.identify(audioChunk) ?: ui.promptForSpeaker()
        convo.addUtterance(speaker, transcript)
        ui.renderMessage(speaker, transcript)
        summarizer.maybeUpdate(convo)
    }
}
```

## Export & Operations
- **Outputs:** Full transcript (JSON), speaker-tagged chat log (Markdown/HTML), and summarized bullet points.
- **Storage:** Local cache of audio chunks and embeddings; cloud sync optional.
- **Privacy:** Offline-first; cloud STT/TTS only when explicitly enabled.

## Next Steps
- Scaffold the shared core modules (Gradle Kotlin Multiplatform) and CI for desktop/Android builds.
- Integrate ONNX Runtime and test Whisper large-v3 Farsi accuracy with sample data.
- Implement diarization enrollment UX (“who is this?”) and embedding cache.
- Add summarization prompts tuned for meetings and evaluate with real recordings.
- Ship early beta builds for Android and desktop to evaluate latency, diarization accuracy, and noise handling.

## Current Implementation Snapshot
- Kotlin JVM project scaffolded with core models and interfaces for audio, STT, diarization, TTS, summarization, and conversation state.
- `MeetingPipeline` wires VAD, denoise, STT, diarization, and summarization hooks; now includes enrollment updates for unknown speakers.
- Added heuristic `EnergyCentroidDiarizationEngine`, `KeywordSummarizer`, console demo (`App.kt`), and Markdown/JSON exporters as smoke-test utilities.
- Added a file-based transcript store that snapshots utterances/speakers to timestamped Markdown and JSON for early persistence.
- Added a file-backed speaker registry store to keep diarization labels consistent across demo sessions.
- Replace heuristics and stubs (`SimpleVad`, `WhisperOnnxStub`, `StubDiarizationEngine`, `StubTtsEngine`, `KeywordSummarizer`) with ONNX/LLM-backed engines to reach production quality.

See `docs/progress.md` for the latest execution plan and percentage breakdown.
# Meeting Transcriber

High-level architecture for a cross-platform (Windows/macOS/Linux, optional Android thin client) meeting assistant with Farsi-first speech-to-text, text-to-speech, speaker identification, silence-triggered capture, and automated summaries governed by measurable quality gates plus smoke-test fixtures, privacy safeguards (consent + retention + audit logging), operational observability, network/media hardening, governance/compliance controls, offline resilience tiers, detailed data/packaging/recovery plans, hardened configuration/secret handling, release-gated testing, RTL-first accessibility validation, deployable desktop/server bundles with deterministic model delivery, a threat/abuse playbook, phased delivery roadmap, newly documented SLOs/migrations/rollback/backfill guidance, manual QA checklists, high-risk defenses, supply-chain/provenance/licensing safeguards, performance engineering and hardware sizing playbooks, prompt-safety/red-team guidance, dataset governance with continuous evaluation, capacity planning and cost controls, role-based onboarding/help, enterprise controls, chaos/incident readiness drills, in-app feedback/support loops, an end-to-end test matrix with traceability, change-control/hotfix workflows, post-release monitoring/ELS guardrails, vulnerability response, compatibility/migration policies, release communication controls, operational dashboards + SOP/runbook templates, a data lifecycle playbook, and a PR-by-PR execution plan for shipping the product.

See [docs/architecture.md](docs/architecture.md) for the proposed system design, technology choices, PR-by-PR execution plan, acceptance criteria/checklist for each increment, the production readiness + Definition of Done gates for release, and the Product Build Blueprint (repo layout, MVP slice, CI commands, and exit criteria) to take this into a shipped product.

The initial scaffolds for that blueprint now live in `desktop-app/` (JavaFX shell) and `python_services/` (service-side stubs exposing deterministic REST endpoints, runnable with `python -m python_services`). The Python services include a lightweight session orchestrator that stitches STT/diarization/summarization together, a simple VAD span detector to gate when chunks should be sent to STT, a raw-audio buffer (`/sessions/{id}/audio`) to stage capture before diarization, a buffer processor (`/sessions/{id}/process_buffer`) to VAD/diarize staged PCM with transcript hints, and a VAD-driven `/sessions/{id}/ingest` hook that appends diarized segments when speech is detected. They capture speaker labels for "who is this?" prompts, let clients set meeting metadata (title + agenda), and export meeting manifests (metadata + segments + summary) for download or persistence until the production pipeline is wired, and stored manifests can be restored into the in-memory session store to resume timelines after restarts. Requests carry request identifiers by default, can be API-key protected, gated by optional rate limiting, and surfaced to browsers via configurable CORS headers; a `/metrics` snapshot exposes request counters for lightweight observability; export manifests can be written to disk, privacy helpers can redact speakers or delete sessions/exports, and a retention sweeper (configurable via env or API) keeps persisted artifacts bounded so the scaffold can sit safely behind gateways while full authN/Z lands. Dockerized runners and deterministic CLI harnesses (`python -m python_services.scripts.demo_session` for the demo flow, `python -m python_services.ops.smoke` for an API smoke) make it easy to exercise the scaffold end-to-end without local Python tooling; the `MeetingAssistantClient` helper plus `python -m python_services.scripts.http_client_demo` extend that to HTTP integrations so the desktop shell can call the scaffold directly. Stored exports can also be downloaded as Markdown or plain text (including metadata, summaries, and labeled timelines) for quick sharing while the production pipeline is wired up.
Sessions now include a `/sessions/{id}/search` keyword endpoint (also exposed in the `MeetingAssistantClient`) so desktop and mobile UIs can light up "find in meeting" flows using diarized text and speaker labels. A `/support/bundle` hook returns a deterministic diagnostics ZIP (settings, counters, active sessions, and stored exports) to keep the scaffold debuggable behind gateways without extra tooling.
