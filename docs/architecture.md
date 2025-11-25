# Architecture Notes

This document expands on the blueprint for a cross-platform Farsi meeting transcriber.

## Technology Stack
- **Language:** Kotlin/Java shared core for Android and desktop.
- **UI:**
  - Android: Jetpack Compose.
  - Desktop: Compose Multiplatform or JavaFX.
- **ML Runtime:** ONNX Runtime for Whisper STT, Silero VAD, PyAnnote-like diarization, and RNNoise/NSNet2 denoising.
- **LLM Runner:** Local inference via GGUF models (Llama 3 Instruct) with llama.cpp bindings, plus optional cloud fallback.

## Core Packages
- `core/audio` – microphone capture, ring buffer, denoise, VAD gating, silence-based flush, audio chunk serialization.
- `core/stt` – Whisper ONNX wrapper, language config (`fa`), timestamp alignment, streaming partials.
- `core/diarization` – speaker turn detection, embedding extraction, similarity search, unknown-speaker hook for UI prompt.
- `core/tts` – provider interface with Coqui/Azure implementations, rate/pitch controls, and caching.
- `core/summarization` – prompt templates, chunked transcripts, and export builders.
- `ui/chat` – chat-style rendering, “who is this?” prompt, and speaker color assignment.
- `ui/export` – Markdown/JSON exporters and file pickers per platform.

## Event Pipeline
1. **Capture Thread:** Streams PCM frames into a ring buffer; denoise in-place.
2. **VAD Gate:** Silero marks speech segments; on speech end, an `AudioChunkReady` event fires.
3. **Transcription Worker:** Converts chunk to mel-spectrogram and runs Whisper ONNX; emits `TranscriptReady` with timestamps.
4. **Diarization Worker:** Generates embeddings for the chunk; searches the embedding store; when unknown, UI prompts for speaker name and stores the mapping.
5. **Conversation Store:** Accepts `(speaker, text, start, end)`; notifies UI to render chat bubble.
6. **Summarizer:** Periodically runs over conversation history to produce bullet points and action items; caches outputs for export.
7. **TTS Playback:** On user request, synthesizes selected utterances and plays via platform audio.

## Data Models
- `Utterance`: `{id, speakerId, text, startTime, endTime}`
- `Speaker`: `{id, displayName, embedding, enrollmentClips[]}`
- `Summary`: `{highlights[], actionItems[], decisions[]}`
- `TranscriptExport`: `{utterances[], speakers[], metadata}`

## Noise & Focus Strategy
- Apply RNNoise/NSNet2 denoising before VAD.
- Track per-speaker energy and SNR; prioritize the active speaker for diarization confidence.
- For multi-mic setups, beamform towards the dominant speaker using WebRTC AEC/beamforming utilities where available.

## Security & Privacy
- Default to offline models; require explicit opt-in for cloud STT/TTS.
- Encrypt cached embeddings and transcripts; allow per-meeting data purge.

## Testing Ideas
- Golden audio clips with expected transcripts and diarization labels.
- Latency benchmarks for VAD-trigger-to-display on Android/desktop.
- Subjective MOS tests for TTS voices.
- Summarization quality evaluation with meeting datasets.
