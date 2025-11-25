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
