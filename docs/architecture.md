# Meeting Transcriber Application Architecture

## Objectives
- Cross-platform desktop app (Windows/macOS/Linux) with emphasis on Java ecosystem and high audio quality. A thin Android shell can reuse the Python services over the network if mobile capture is needed.
- Accurate Farsi speech-to-text (STT) and text-to-speech (TTS).
- Speaker diarization with on-the-fly identification and prompting for unknown speakers.
- Silence detection to chunk audio quickly for transcription.
- Summarization of meetings and focus on the dominant speaker in noisy environments.
- Reproducible quality gates: establish accuracy/performance thresholds and automated evaluations before releasing binaries.

## Platform and Framework
- **Desktop shell:** Java 21 with JavaFX for native-feeling UI across Windows/macOS/Linux. Compose Multiplatform is a viable alternative if Kotlin is preferred, but the JavaFX path keeps Farsi font rendering predictable across OSes.
- **Android (optional):** Minimal Kotlin app that streams PCM to the Python/Cloud endpoints; reuse VAD on-device (WebRTC VAD via Oboe/AAudio) and render the same chat-style UI with Jetpack Compose.
- **Audio & ML services:** Host heavier ML workloads in a **Python sidecar** (gRPC/REST), letting Java focus on UI and streaming audio. This keeps vendor flexibility for STT/TTS and diarization models.
- **Packaging:** Use jlink/jpackage for Java app; embed Python env via installer or require runtime download.

## Core Components
1. **Audio Capture & Preprocessing (Java)**
   - Capture microphone input via `javax.sound.sampled`.
   - Apply noise suppression and automatic gain control (WebRTC AudioProcessing bindings).
   - Real-time **voice activity detection (VAD)** to detect silence and emit audio segments for STT with minimal latency.

2. **Streaming Gateway (Java ↔ Python)**
   - Maintain bi-directional gRPC stream for audio frames and transcription responses.
   - Attach metadata (speaker tag, segment timestamps, confidence) to each transcript chunk.
   - Enforce bounded in-flight buffers (e.g., 3–5 segments) with backpressure signals to avoid overruns on low-end CPUs.

3. **STT (Python service)**
   - Prioritize Farsi accuracy: **OpenAI Whisper large-v3** or **WhisperX** (faster alignment) with GPU support if available.
   - Optional lightweight/offline fallback: **Vosk Farsi** model for CPUs.
   - Return partial hypotheses quickly; finalize segments on silence boundaries.
   - **Quality guardrails:** track WER on a held-out Farsi evaluation set; reject builds exceeding 15% WER or 800 ms median first-token latency on desktop GPU tests.

4. **Speaker Diarization & Identification (Python service)
   - Use **pyannote.audio** (Diarization 3.1) or **SpeechBrain ECAPA** embeddings for diarization.
   - Maintain an **embedding gallery**; when a new cluster appears, Java UI asks “Who is this?” to label and store embedding → persistent profile store.
   - Add periodic **gallery re-embedding** to keep vectors consistent after model upgrades; store embedding version in the DB.
   - **Robustness:** run overlap-aware diarization and energy-based re-segmentation to keep DER < 10% on noisy mixes.
   - Add **voice spoof checks** (e.g., simple spectral flatness/zero-crossing heuristics) before accepting a new speaker label to reduce mislabeling from background media.

5. **TTS (Python service)**
   - High-quality Farsi: **Microsoft Azure Neural Farsi** or **Google Cloud Wavenet** voices; fallback to **Coqui TTS Farsi** (local VITS model).
   - Stream audio back to Java for playback and notifications.
   - Cache frequent prompts (greetings, confirmations) to avoid cloud latency where possible.
   - Normalize phonemes for **names captured from speaker prompts** to keep pronunciation consistent between STT and TTS.

6. **Summarization (Python service)**
   - Aggregate transcript with speaker tags.
   - Produce bullet highlights and action items using an LLM (e.g., GPT-4o-mini or local Llama 3 8B-instruct for offline).
   - Export as Markdown/HTML/PDF.
   - Add **recall and faithfulness checks** using QA-style prompts over the transcript; flag low-confidence summaries in the UI.
   - Provide **sentence-level traceability**: each bullet links back to transcript timestamps so users can verify intent quickly.

7. **UI/UX (JavaFX)**
   - Timeline view with color-coded speakers; side panel chatbox shows “Name: quotation”.
   - Prompt dialog when diarization finds an unknown speaker.
   - Controls: start/stop capture, device chooser, noise reduction toggle, export summary.
   - Visual indicator of active speaker energy to “focus” UI on dominant speaker during noise.
   - **Accessibility:** ship with preferred Farsi fonts bundled; include right-to-left rendering validation in CI screenshots.
   - **Trust cues:** show STT confidence + diarization certainty on hover; add a “play original audio” button per utterance.

## Data Flow
1. Java captures audio → VAD segments → gRPC stream to Python.
2. Python performs STT and diarization; sends interim/final transcripts with speaker labels.
3. Java UI displays live chat-style feed (`Speaker Name: text`).
4. On unknown speaker, UI prompts for name; Java sends label + embedding ID back to Python for gallery update.
5. After meeting, Java requests summary → Python LLM returns key points → Java exports file.

## Noise Robustness
- Use WebRTC denoise + automatic gain.
- Diarization with overlapping speech support (pyannote overlap handling).
- “Focus main speaker” UI behavior: emphasize highest-energy/most-recent speaker; optionally duck TTS playback.
- Record short **noise profiles** on startup to adapt suppression to each room.
  - Persist per-device noise profiles (identified by OS device ID) to avoid re-training each session.
  - Expose a “recalibrate noise profile” action in settings for changing environments.

## Storage
- Lightweight SQLite DB (via JDBC) to store meetings, transcripts, speaker profiles (embedding IDs + names), and summaries.
- Audio segments stored as compressed FLAC/OGG for archival.
- Speaker embeddings and profiles synced via encrypted export/import to keep identities portable across machines.
 - Add a **media quarantine folder** for segments flagged as low-confidence diarization so reviewers can relabel before inclusion.

## Deployment Notes
- Bundle model weights optionally downloaded on first run with checksum verification.
- GPU detection in Python service to select optimal STT/TTS models.
- Provide **offline installer** with the smallest functional Vosk + Coqui models and allow deferred download of large Whisper/pyannote weights.
- Ship **sample fixtures** (short multi-speaker Farsi clips) with expected transcripts/DER to validate install integrity.

## Security & Privacy
- Default to **local processing** when GPU/CPU resources are sufficient; prompt before sending audio to cloud STT/TTS.
- Encrypt on-disk artifacts: transcripts, speaker embeddings, and cached TTS outputs via OS keystore-backed keys.
- Use **TLS with mutual auth** between Java client and Python service when separated across hosts; pin certificates for cloud endpoints.
- Redact sensitive entities (names, phone numbers, IDs) in summaries when exporting; provide a toggle for full transcript export.
- Keep a **consent banner** for new speaker identification prompts and provide “forget speaker” to delete embeddings + history.
- Integrate **anti-spoof checks** before adding/updating profiles; flag suspicious segments for manual review in the quarantine folder.
- Add a **data retention policy**: default 30–90 day retention for raw audio, configurable by tenant; enforce auto-deletion via
  background jobs and expose a “purge now” control in settings.
- Keep an **audit log** for consent prompts, profile creation/updates/deletions, export requests, and cloud processing toggles;
  ship a script to redact or rotate audit logs when users invoke “forget speaker.”
- Store **policy version** alongside artifacts (transcripts, embeddings) so upgrades can enforce stricter defaults without
  corrupting older exports; block imports created with weaker/unknown policy versions until re-consented.

## Observability & Operations
- Log structured events for VAD triggers, STT finalizations, diarization label changes, and TTS cache hits/misses.
- Emit metrics: end-to-end latency p50/p95, VAD false-positive/false-negative rates, DER/WER drift against fixtures, dropped frames, and GPU/CPU utilization.
- Provide a **debug trace mode** that saves aligned waveform + transcript snippets for support tickets (auto-expire in 24 hours by default).
- Add health endpoints: `/healthz` (process up), `/readyz` (models loaded), `/metrics` (Prometheus).
- Include **log redaction** for PII in telemetry; separate clean-room crash reports from content data.
- Ship a lightweight **operational runbook** alongside installers: start/stop commands, common error signatures (e.g., missing CUDA), and remediation steps.

## Resilience & Offline Behavior
- Cache critical assets (fonts, UI strings, offline models) to allow **air-gapped transcription** with degraded accuracy.
- When Python service is unreachable, queue audio locally and retry; surface backlog status in the UI.
- Implement **graceful degradation tiers**: Tier 1 (full Whisper+pyannote+cloud TTS), Tier 2 (Whisper small + local VITS), Tier 3 (Vosk + on-device heuristics), with clear UI banners.
- For intermittent connectivity on Android thin client, persist captured PCM chunks and **upload with checksum validation** when a connection resumes.
- Add watchdogs for stalled streams: if no transcript arrives in N seconds, recycle gRPC stream and alert the user.
- Auto-rotate diarization galleries when embeddings are stale (>90 days) or exceed size thresholds; prompt to archive rarely seen speakers.


## Data Model & Storage Details
- **SQLite schema (desktop):**
  - `speakers(id INTEGER PK, name TEXT, embedding BLOB, embedding_version TEXT, created_at, updated_at, consent_version TEXT)`
  - `meetings(id INTEGER PK, started_at, ended_at, policy_version TEXT, device_id TEXT, noise_profile_id TEXT)`
  - `segments(id INTEGER PK, meeting_id FK, speaker_id FK NULLABLE, start_ms INTEGER, end_ms INTEGER, transcript TEXT, confidence REAL, audio_path TEXT, quarantine BOOLEAN DEFAULT FALSE)`
  - `summaries(meeting_id FK, markdown TEXT, html TEXT, pdf_path TEXT, faithfulness_score REAL)`
  - `audit(id INTEGER PK, meeting_id FK NULLABLE, actor TEXT, action TEXT, payload JSON, created_at)`
- **Noise profiles:** stored per device ID with checksum; revalidated on startup and rotated if device driver version changes.
- **Backups/exports:** compress SQLite + media + embeddings into a tarball with manifest: policy version, model versions, hashes. Reject imports when manifest version is lower than current minimum supported.
- **Cloud/remote mode:** swap SQLite for Postgres; enforce row-level encryption on sensitive columns (embeddings, transcripts) using application-layer keys derived from the user keystore.

## Install, Update, and Packaging
- **Install smoke test:** after installation, run the bundled 5-second Farsi fixture through VAD → STT → diarization, produce a mini HTML report, and surface a pass/fail badge in the UI’s About dialog.
- **Updaters:** use differential updates for the Java app (jpackage or custom patcher) and a **model asset updater** that fetches only new weights; validate with checksum + signature. Block app launch if asset verification fails until user retries or reverts.
- **Permissions prompts:** first launch should explicitly request microphone permission, keychain/keystore use, and consent to audit logging; cache decisions and allow revocation from settings.
- **Android thin client:** ship an optional asset pack with the small offline Vosk + VITS models; defer Whisper downloads to Wi-Fi only.
- **Crash recovery:** installer drops a `diagnostics` CLI that can collect logs, recent crash dumps, and the latest smoke-test report into a ZIP for support (PII-scrubbed by default).

## Evaluation & Benchmarks
- **Performance baselines (desktop GPU):** first-token latency < 800 ms, median transcription E2E latency < 2.5 s, DER < 10% on 2-speaker noisy mix, and TTS time-to-first-byte < 700 ms with Azure Farsi; publish dashboards and fail CI if drift >10%.
- **Resource usage ceilings:** CPU < 250% and RAM < 3.5 GB for the Python sidecar during typical 2-speaker calls; trigger backpressure when approaching ceilings.
- **Energy/battery checks (Android):** STT/diarization runs capped at 20% battery drain per hour; suspend background upload if below 15% battery unless on charger.
- **Ethics/consent:** verify UI flows in screenshots to ensure consent banner and “forget speaker” controls are present; mandate locale-aware RTL layout snapshots in CI for Farsi.

## Failure & Recovery Playbook
- **Streaming interruptions:** recycle gRPC channels on heartbeat loss; queue up to N segments locally with exponential backoff retries; surface a “Resending…” badge per segment.
- **Model load failures:** fallback to smaller local models and raise a UI banner indicating degraded quality; log model version and checksum for support.
- **Diarization drift:** if DER spikes beyond threshold in live metrics, temporarily disable gallery writes and revert to anonymous speaker tags until drift clears; prompt user to re-run noise calibration.
- **Storage pressure:** enforce quotas; when disk space < 10%, automatically purge expired audio first, then quarantined segments, while preserving audit logs unless the user opts in to purge.
- **Policy mismatches:** when importing archives with older policy versions, present a reconciliation wizard to re-collect consent and re-embed speakers before activation.

## MVP Implementation Steps
1. Scaffold JavaFX app with audio capture + VAD and a chat-style transcript panel.
2. Create Python gRPC service exposing STT (Whisper), diarization (pyannote), TTS (vendor/local), and summarization endpoints.
3. Wire streaming pipeline with interim/final transcripts and speaker prompts.
4. Persist speaker labels/embeddings and meeting transcripts to SQLite.
5. Add export (Markdown/PDF) and UI polish for dominant-speaker focus.
6. Add automated regression checks: VAD boundary precision/recall, diarization DER on synthetic noisy mixes, STT WER on curated Farsi corpus, and latency dashboards for end-to-end capture → transcript → summary.
7. Create a **smoke-test harness** that runs end-to-end on install: record 5 seconds of audio, detect VAD boundaries, run STT/diarization, and show a compact HTML report for support teams.

## Quality/Testing
- Unit tests for audio chunking and VAD boundaries (Java).
- Integration tests that stream sample Farsi audio through the Python service and validate transcript accuracy thresholds and diarization purity.
- UI tests for prompt flow when a new speaker is detected.

## Alternatives
- Cross-platform via **Electron + Node** with Python backend if web tech is preferred.
- Mobile option: reuse Python service in the cloud; Android app in Kotlin streams audio via WebRTC to backend.
