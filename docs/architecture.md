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
- Add **canary mode**: route 1–5% of sessions to the newest STT/diarization models with shadow evaluation against the stable channel; promote only if WER/DER and latency stay within SLOs.
- Keep **profiling presets** (desktop GPU, desktop CPU, Android streaming) and attach flamegraph captures to regression runs to catch bottlenecks in audio pipelines, protobuf serialization, and UI rendering.
- Maintain a **metrics dictionary** (metric name, units, owner, alert thresholds) in source control to avoid drift between code, dashboards, and runbook.

## Network & Media Pipeline Hardening
- Prefer **WASAPI loopback** (Windows), **CoreAudio** (macOS), and **PulseAudio/PipeWire** (Linux) capture paths; ship a compatible mode that records raw PCM if platform bindings fail.
- Keep **audio clock drift correction** between Java capture and Python processing by resampling slowly (e.g., SpeexDSP) and aligning by RTP-style sequence numbers to avoid lip-sync drift in longer meetings.
- Throttle upload bitrate for thin Android clients on unstable networks; prioritize **transcription-critical** frames and defer low-importance telemetry until stable connectivity resumes.
- For remote/cloud Python services, enable **TLS session resumption** and compressed protobuf payloads; fall back to plain JSON over HTTPS if intermediaries block gRPC.
- Add **file format validators** on ingest (sample rate, channel count, duration limits) to reject corrupted captures before STT/diarization runs.

## Resilience & Offline Behavior
- Cache critical assets (fonts, UI strings, offline models) to allow **air-gapped transcription** with degraded accuracy.
- When Python service is unreachable, queue audio locally and retry; surface backlog status in the UI.
- Implement **graceful degradation tiers**: Tier 1 (full Whisper+pyannote+cloud TTS), Tier 2 (Whisper small + local VITS), Tier 3 (Vosk + on-device heuristics), with clear UI banners.
- For intermittent connectivity on Android thin client, persist captured PCM chunks and **upload with checksum validation** when a connection resumes.
- Add watchdogs for stalled streams: if no transcript arrives in N seconds, recycle gRPC stream and alert the user.
- Auto-rotate diarization galleries when embeddings are stale (>90 days) or exceed size thresholds; prompt to archive rarely seen speakers.

## Governance, Compliance, and Data Handling
- Maintain a **data inventory** (tables, fields, retention, lawful basis) alongside the schema; generate it automatically from the migration definitions to reduce drift.
- Provide **data residency controls**: allow users to pin storage to local-only, specific drives, or managed cloud buckets; refuse cross-region uploads when a residency policy is active.
- Ship a **consent receipt** per speaker prompt (timestamp, device ID, policy version) and bundle it with exports so re-imports can re-establish lawful basis.
- Add **pseudonymization mode** that replaces speaker names with stable hashes for shared transcripts, keeping the mapping locally encrypted.
- Include **child-voice safeguards**: if diarization detects high-pitch + short utterances indicative of minors, gate cloud processing and require explicit consent before export.
- Run a **DPIA-style checklist** in CI: encryption at rest/on wire present, retention defaults non-zero, consent prompts visible in screenshots, and audit log storage enabled.
- Document **third-party subprocessor list** (cloud TTS/STT providers) and expose toggles to disable them globally.
- Provide a **right-to-erasure workflow** that scrubs embeddings, audio, transcripts, summaries, and audit entries linked to a speaker ID while keeping aggregate metrics intact.

## Configuration, Secrets, and Policy Management
- **Configuration layers:** default config in repo → packaged overrides per OS → user-level overrides in `~/.meeting-transcriber/config.toml`; use explicit schema validation and reject unknown keys.
- **Secret handling:** store API keys (Azure/Google TTS) in OS keystore; never log secrets; enforce rotation reminders and expiry dates. Permit offline mode when secrets are missing instead of crashing.
- **Policy bundles:** versioned JSON files describing retention limits, consent prompts, export rules, and cloud/online toggles. Embed bundle hash in summaries/exports for auditability.
- **Feature flags:** gate experimental diarization models, canary percentages, and UI trust cues; default to **safe** flags after crashes until the user re-enables them.
- **Configuration audits:** log config diffs on startup and after updates; surface a “policy mismatch” badge if runtime config conflicts with packaged defaults.


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

## Release, Testing, and Promotion
- **CI gate:** run VAD precision/recall, STT WER, DER, TTS latency, and summary faithfulness checks on every merge; block releases when deltas exceed SLOs, and attach artifacts (waveforms, alignments, HTML reports) to the pipeline summary.
- Maintain a **hardware matrix** (CPU-only, mid-tier GPU, Android mid/high) with scheduled nightly runs to catch regression in utilization, thermal limits, and battery consumption.
- Add **fuzz tests** for protobuf/gRPC stream handling and truncated PCM frames to prevent crashes on malformed input.
- Run **determinism checks** for offline models (Whisper/Vosk/Coqui) under fixed seeds; fail when weight drift or env updates change outputs beyond tolerance.
- Ship **canary promotion rules**: require N sessions with equal-or-better WER/DER and p95 latency before flipping feature flag defaults; auto-rollback on elevated error budgets.
- For **installer smoke tests**, publish baseline metrics and tolerances; record pass/fail + perf numbers into a local history DB so support can trace changes across app updates.

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
- **LLM safety:** summarize with grounded prompts that reference transcript spans; add **hallucination suppressors** (e.g., require citeable spans per bullet). Reject summaries when faithfulness score falls below threshold and keep the transcript-only export available.
- **TTS quality checks:** include pronunciation regression tests for common Farsi names and honorifics; detect SSML failures and retry with simplified text. Mark cached TTS clips with the model voice and locale used.
- **Adversarial audio tests:** maintain a suite with background TV/radio, overlapping speakers, and microphone handling noise; track DER/WER/latency across these stressors.

## Failure & Recovery Playbook
- **Streaming interruptions:** recycle gRPC channels on heartbeat loss; queue up to N segments locally with exponential backoff retries; surface a “Resending…” badge per segment.
- **Model load failures:** fallback to smaller local models and raise a UI banner indicating degraded quality; log model version and checksum for support.
- **Diarization drift:** if DER spikes beyond threshold in live metrics, temporarily disable gallery writes and revert to anonymous speaker tags until drift clears; prompt user to re-run noise calibration.
- **Storage pressure:** enforce quotas; when disk space < 10%, automatically purge expired audio first, then quarantined segments, while preserving audit logs unless the user opts in to purge.
- **Policy mismatches:** when importing archives with older policy versions, present a reconciliation wizard to re-collect consent and re-embed speakers before activation.

## Localization, Accessibility, and UX Validation
- **RTL correctness:** run screenshot-based visual tests for right-to-left layout, proper ligatures, and alignment of chat bubbles; treat RTL regressions as release blockers.
- **Screen-reader support:** label controls for voiceover/TalkBack; ensure live transcript updates are announced without overwhelming the user (throttled announcements with priority for new speakers).
- **Input methods:** validate Persian keyboard input for speaker names and search; handle mixed-script queries when filtering transcripts.
- **Color and motion:** respect OS high-contrast/reduced-motion preferences; provide a monochrome theme option for projector readability during meetings.
- **Idle/privacy states:** add a “privacy curtain” that hides transcripts when the window loses focus or on user request; show obfuscated previews until reactivated.

## Supply Chain, Licensing, and Attribution
- **Dependency policy:** pin Python and Java dependencies with lockfiles (e.g., `requirements.txt` + hashes, Gradle version catalogs) and enforce license allowlists (Apache/MIT/BSD) via automated scans in CI.
- **Third-party models:** store license/usage terms for Whisper, pyannote, Vosk, Coqui, and Azure/Google TTS; surface a **licenses** view in the app and export bundle to fulfill attribution.
- **Binary provenance:** sign installers and sidecar wheels; publish SBOMs (CycloneDX) for each release and verify signatures during updates. Refuse unsigned updater payloads.
- **Model authenticity:** require signature+checksum verification before activating new model assets; quarantine and alert on mismatches, keeping previous assets active.
- **Reproducible builds:** document deterministic build flags (e.g., `SOURCE_DATE_EPOCH`, stripped timestamps in archives) so support can reproduce shipped binaries.

## Performance Engineering Playbook
- **Profiling presets:** preconfigure async-profiler/JFR for Java UI and PyTorch profiler for the Python sidecar; ship scripts to capture 30–60 second traces with privacy scrubbing of transcript text.
- **Hot-path audits:** profile VAD→gRPC→STT→UI loop under CPU-only and GPU modes; budget time per stage and fail builds that exceed the budget by >10%.
- **Frame pacing:** align capture buffer sizes with model stride (e.g., 20–30 ms frames) to avoid jitter; log buffer overruns and adaptively reduce frame size when underruns occur.
- **GPU safeguards:** monitor VRAM usage and auto-downgrade model sizes when fragmentation or memory pressure is detected; expose a UI banner when falling back.
- **Thermal management (Android):** reduce diarization frequency or switch to offline lightweight STT when thermal throttling is detected; delay non-critical uploads until cool-down completes.

## Supportability and Field Operations
- **Tiered diagnostics:** expose three levels—basic (health + versions), sensitive (recent logs, redacted transcripts), and deep (short audio slices + embeddings hashed); default to basic and require explicit consent for deeper levels.
- **Guided troubleshooting:** add a “Fix it” wizard that walks users through microphone checks, network reachability to the Python service, and model asset validation before opening a ticket.
- **Runbook links in-app:** surface contextual help URLs for common errors (model load failure, policy mismatch, consent required) with remediation steps from the ops runbook.
- **Incident markers:** allow support to mark a session as “investigation pending,” preserving logs/metrics beyond normal retention while respecting consent for audio storage.
- **Telemetry minimization:** for opted-in analytics, strip transcript text and send only aggregated counters/hashes; expose a toggle in setup and settings.

## Delivery Roadmap (Expanded)
- **M0 (2–3 weeks):** local-only desktop prototype with VAD, Whisper small, basic diarization, chat UI, and manual speaker naming; ship installer smoke test and privacy curtain.
- **M1 (4–6 weeks):** integrate gallery persistence, Azure/Google TTS, summary export, and audit/consent logging; add deterministic model download and policy bundles.
- **M2 (6–10 weeks):** backpressure/tuning for GPU + CPU, overlap-aware diarization, trust cues, RTL/accessibility tests, and support bundle CLI; start canary promotion rules.
- **M3 (10–14 weeks):** rollout governance (data residency, erasure), hardware-matrix CI, adversarial audio suite, auto-noise profiling, and configuration audits.
- **M4 (14–18 weeks):** refine performance (profiling presets, GPU fallbacks), deliver Android thin client with offline pack, enable signed updates, and complete compliance/attribution UI.
- **M5 (18–22 weeks):** production hardening: SBO M + signature enforcement, field telemetry with opt-in, incident markers, and fully automated rollback + policy reconciliation flows.

## Deployment, Packaging, and Environment Strategy
- **Target bundles:** ship desktop binaries per OS (Windows .msi, macOS .pkg/.dmg notarized, Linux .deb/.rpm/AppImage) with an embedded JRE and optional embedded Python env. Offer a “lean” installer that downloads models on first run to cut initial size.
- **Runtime separation:** isolate Python sidecar into its own process with signed wheels and pinned hashes; prefer **venv + uv** for deterministic dependency sync. On macOS, harden runtime with entitlements for microphone/file access only.
- **Model delivery:** cache models under an app-specific directory (`AppData`, `~/Library/Application Support`, `$XDG_DATA_HOME`), versioned by checksum. Add a background job to prune superseded models while honoring retention windows.
- **Update policy:** delta-updates via background downloader with rollback to the previous signed bundle. Block upgrades when policies/configs are incompatible without explicit user consent.
- **Hybrid deployment:** allow remote Python services when a GPU is unavailable; enforce TLS + mutual auth for LAN/cloud connects. Provide a self-hosted Docker Compose stack with GPU-enabled images and a CPU-only override profile.

## Data Governance, Storage, and Retention Flows
- **Schema highlights:**
  - `meetings` (id, title, start/end time, consent_version, retention_policy_id).
  - `segments` (meeting_id, start/end timestamps, speaker_id, transcript_text, model_version, vad_score, confidence, checksum).
  - `speakers` (id, display_name, embedding_vector, embedding_version, enrollment_audio_hash, last_seen, trust_state).
  - `artifacts` (meeting_id, type=audio|summary|export, path/hash, created_at, encrypted=true/false, purge_after).
- **Retention automation:** store retention policies in a table with duration + scope; a nightly job sweeps expired `artifacts` and `segments`, skipping audit logs unless the user opts in to purge.
- **Consent receipts:** persist consent prompts with timestamp, locale, policy version, and capture device. Include an exportable PDF/HTML receipt for compliance queries.
- **Data subject rights:** add endpoints/CLI to export or purge a single speaker profile and their associated segments; re-run diarization to anonymize remaining text when purging embeddings.
- **Encryption & keys:** encrypt artifacts at rest with OS keychain-protected keys on desktop; on the server, use envelope encryption per tenant. Rotate keys with a migration job that rewrites artifacts and updates key metadata.

## Threat Model and Abuse Handling
- **Privacy threats:** microphone hot-mic risk → require explicit capture toggle with clear status indicator; auto-stop capture on OS session lock; audit every microphone activation.
- **Spoofing/impersonation:** enforce liveness challenges during new-speaker enrollment (prompt to read a random Farsi phrase); flag sudden voiceprint deviations and pause auto-labeling until user confirmation.
- **Tampering:** verify signed updates, validate model checksums before load, and enforce HTTPS/TLS 1.2+ with pinned backends for remote services.
- **Data exfiltration:** sandbox file access to app directories; require user confirmation for exports leaving the machine; redact PII from summaries by default unless the user requests otherwise.
- **Abuse reporting:** provide a one-click “Report misuse” that packages logs (with PII redaction) and current policy versions for support.

## Observability and Alerting Runbook
- **Metrics minimums:**
  - gRPC E2E latency percentiles (p50/p95) for capture → transcript → summary.
  - DER/WER rolling averages and model version tags.
  - VAD false-positive/false-negative rates on daily samples.
  - TTS time-to-first-byte and synthesis duration.
  - Resource gauges: CPU/RAM/VRAM, queue depth, dropped frames.
- **Alerting:**
  - Page when DER or WER exceeds thresholds for 3 consecutive runs.
  - Warn when disk space < 15% or model cache exceeds quota.
  - Notify when speaker gallery trust score drops (potential spoof) or when consent receipts fail to persist.
- **Log hygiene:** structured logs with correlation IDs per meeting; redact transcripts by default but allow protected debug logging with short TTL for support. Keep a **data-handling ledger** log stream for audit trails.
- **Dashboards:** per-OS health widgets, Android battery/throughput charts, and cache hit/miss panels. Include a privacy mode that hides PII in dashboards for demos.

## Delivery Roadmap (Phased)
1. **Foundations (Weeks 1–3):** scaffold JavaFX UI, VAD pipeline, gRPC stubs, and local Python service with Whisper + pyannote + Azure TTS; ship smoke-test harness.
2. **Quality Gating (Weeks 4–6):** add evaluation corpora, DER/WER dashboards, RTL/accessibility tests, and automated policy/consent flows; implement retention sweeper.
3. **Resilience & Security (Weeks 7–9):** add backpressure, offline queueing, signed update channel, encryption at rest, liveness checks for enrollment, and sandboxed export flows.
4. **Optimization & Mobile (Weeks 10–12):** tune latency/resource ceilings, add Android thin client with remote Python option, and ship GPU/CPU Docker images.
5. **GA Readiness (Weeks 13–14):** finalize runbook, alerts, support tooling (“Report misuse”), and freeze model versions with reproducible build manifests.

## Open Risks and Mitigations
- **GPU scarcity:** fall back to CPU Vosk + smaller pyannote checkpoint; gate latency expectations accordingly and message “degraded mode” in UI.
- **Accented Farsi coverage:** expand corpora with regional dialect samples; allow per-meeting acoustic adaptation and prioritize names/keywords via contextual biasing.
- **Background TV/music bleed-through:** train/adopt separation/denoising frontends; add a “conference room” preset that tightens VAD thresholds and applies aggressive suppression.
- **Long-meeting drift:** periodically re-align transcripts with WhisperX alignment and refresh dominant-speaker scores; chunk summaries hourly to avoid context loss.
- **User trust & consent fatigue:** cache previously accepted policy versions per device and prompt only on material changes; provide concise, localized summaries of what changed.

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

## Operational SLOs and Support Tooling
- **Availability:** Python sidecar ready < 45 seconds after app start; transcript streaming uptime > 99% during a meeting.
- **Latency:** end-to-end capture → transcript p95 < 3.5 s on desktop GPU; Android thin client upload jitter < 250 ms p95.
- **Quality:** WER < 15% and DER < 10% on the reference suite; summarize faithfulness score > 0.75 before display.
- **Data safety:** zero known-loss incidents for transcripts/audio; failed writes auto-retry with idempotent segment IDs.
- **Support bundle:** one-click “Collect diagnostics” produces redacted logs, recent crash dumps, latest smoke-test report, policy bundle hash, and hardware profile (CPU/GPU/driver) for triage.
- **Self-heal:** watchdog restarts sidecar on healthcheck failures; UI surfaces countdown and rolls over to degraded mode if restart fails twice.

## Migration, Rollback, and Backfill Guidance
- **Schema migrations:** versioned SQL migrations with preflight checks for disk space and backup availability; block upgrades if retention/audit tables are missing indexes that guard sweeps.
- **Backfills:** enqueue idempotent jobs to recompute embeddings when model versions change; tag partially processed rows and resume on next launch.
- **Rollback:** keep previous app + model bundles for two versions; rollback script restores prior SQLite/Postgres snapshot and clears incompatible caches.
- **Data imports:** enforce manifest compatibility before ingest; dry-run option validates hashes and policy versions without writing.
- **Index hygiene:** periodic VACUUM/ANALYZE (SQLite) or REINDEX (Postgres) scheduled during idle hours; alert when table bloat exceeds 20% of base size.

## Manual QA and Field Validation Checklist
- **Capture & VAD:** verify start/stop hotkey, device switch mid-call, and accurate silence-triggered chunking using the bundled fixture and a live mic.
- **Diarization & prompts:** confirm unknown-speaker prompt fires within 2–3 utterances; test overlapping speakers and enrollment liveness challenge.
- **TTS:** exercise Farsi pronunciation for common names/honorifics, SSML fallback, and cached prompt reuse; confirm playback ducking when focus-on-speaker is active.
- **Summaries:** validate timestamped bullets, faithfulness score display, and the ability to jump back to audio from a bullet.
- **Resilience:** simulate network drop (pull cable/disable Wi-Fi) and confirm queued uploads + checksum replay on reconnect; kill the sidecar process to ensure watchdog recovery.
- **Privacy/consent:** check banner visibility, “forget speaker” flow (scrubs embeddings + segments + audit entries), and that exported transcripts respect pseudonymization.
- **Localization/accessibility:** run RTL screenshot comparison, screen-reader announcement for live transcript updates, and high-contrast theme toggles.

## High-Risk Scenarios and Defenses
- **Cross-talk in noisy rooms:** run separation/denoise preset; emphasize highest-energy speaker in UI and quarantine low-confidence segments for review.
- **Playback interference:** detect loopback/feedback by checking near-zero-latency echo patterns; auto-lower TTS volume and prompt to mute speakers.
- **Adversarial audio or spoofed enrollment:** enforce randomized enrollment phrases, run anti-spoof heuristics, and require user confirmation before updating trusted gallery entries.
- **Resource exhaustion:** apply CPU/VRAM budgets per process; shed load by reducing VAD sensitivity and downgrading model sizes before dropping audio.

## Prompt Hygiene, Red-Teaming, and Safety
- **Grounded prompting:** all LLM summarization prompts must include a structured transcript slice plus citation requirement; reject model responses lacking timestamp back-links.
- **Prompt-injection defenses:** strip/escape markup, block directives asking to ignore policy, and cap prompt size; add a detector for “ignore instructions”/“speak as” phrases and fall back to rule-based summaries if triggered.
- **Toxicity/PII filters:** run lightweight classifiers on summaries and redact obvious PII (IDs, phone numbers) before display; keep the raw transcript available behind a “view raw” gated control.
- **Red-team corpus:** maintain adversarial prompt/audio examples (in Farsi and mixed-language) that attempt jailbreaks, persona hijacks, or malicious SSML; fail CI if summaries deviate from policy-compliant outputs.
- **Replay detection:** tag inputs with meeting/session IDs and drop repeated payloads to prevent replay of manipulated segments; audit rejected attempts.

## Data Governance and Corpus Management
- **Dataset lineage:** version training/eval corpora with checksums, consent status, and license; block ingestion of clips lacking provenance or consent receipts.
- **Bias review:** track diarization/STT accuracy by gender/region/accent; add CI checks to ensure no cohort regresses >3 p.p. DER/WER across releases.
- **Human labeling SOPs:** document labeling playbooks (timestamp granularity, overlap guidelines, anonymization rules) and require two-pass review for new benchmark additions.
- **Corpus minimization:** rotate out stale meeting clips after N months; keep only fixtures necessary for regression and a minimal “stress” suite for fuzz tests.
- **Access control:** store corpora and embeddings in encrypted volumes with role-based access; require dual control for exports of labeled datasets.

## Edge Deployments and Enterprise Controls
- **Air-gapped mode:** ship an offline updater bundle (SBOM + signed model/assets) for environments without internet; surface a “last-updated” watermark and warn when policy bundles are stale.
- **Enterprise auth:** allow SSO (OIDC/SAML) for cloud mode; map identity to consent/audit records and restrict export/erasure actions by role.
- **Device trust:** optionally enforce **device attestation** (Windows Hello/Platform attestation or macOS notarization checks) before enabling microphone capture in managed environments.
- **Firewall-friendly transport:** provide HTTPS long-polling fallback when gRPC is blocked; throttle retry storms and expose a diagnostics probe for network allowlisting.
- **Local policy overrides:** permit enterprises to enforce stricter retention/telemetry defaults; show an immutable “managed by org” banner when overrides are active.

## Documentation, Training, and Change Management
- **User guide:** ship an in-app handbook with RTL-aware screenshots for capture, consent, gallery enrollment, exports, and offline mode; include troubleshooting trees for common failures.
- **Release notes:** publish per-version change logs summarizing model upgrades, policy changes, and known issues; persist locally so users can review offline.
- **Admin playbook:** provide ops runbooks for backups, key rotation, SBOM signature validation, and responding to failed smoke tests; keep commands copy/pasteable.
- **Training mode:** add a sandbox that replays bundled fixtures through the UI for training new users without recording live audio; disable export in this mode to prevent leakage.
- **Change audits:** log schema/config/policy version bumps with responsible actor and rationale; require explicit acknowledgement in-app after major behavior changes (e.g., new retention defaults).
- **Clock drift across devices:** align segments with monotonic timestamps and resample slowly to avoid transcript timing skew in long sessions.

## Licensing, Provenance, and IP Compliance
- **SBOM and license auditing:** ship an SBOM with SPDX identifiers for all dependencies/models; block builds if license scanners (e.g., OSS Review Toolkit) find non-compliant copyleft in app clients or embedded assets.
- **Content provenance:** propagate source metadata (speaker, device, session, consent ID) into transcript and embedding records; include signatures/hashes for model and policy bundles so downstream exports retain cryptographic proof of origin.
- **Attribution and notices:** auto-generate NOTICE/third-party acknowledgements in-app and in installers (Windows/macOS/Android) from the SBOM; keep localized Farsi/English versions.
- **Media rights checks:** before exporting audio clips or synthesized voices, require an explicit confirmation that the requester has rights/consent; log the attestation alongside the export manifest for audits.

## Chaos Engineering and Incident Readiness
- **Fault injection:** rehearse gRPC dropouts, stalled TTS responses, and corrupted policy bundles in staging; verify clients fail closed (e.g., stop capture, show privacy curtain) rather than leaking audio.
- **Game days:** schedule quarterly drills that simulate cloud outages, revoked certificates, or adversarial firmware updates; measure MTTD/MTTR against SLOs and update runbooks with findings.
- **Load shedding verification:** automate tests that ratchet CPU/GPU pressure and ensure the app gracefully downgrades models/VAD sensitivity before dropping audio, with clear UI banners.
- **Post-incident reports:** standardize RCA templates (timeline, user impact, detection gaps, owner, follow-ups) and require publication within 72 hours for Sev-1 incidents.

## Performance Tuning and Hardware Sizing
- **Latency budgets:** set end-to-end targets (e.g., <800 ms STT partials, <400 ms TTS kickoff) and track them per platform/hardware tier; block releases if P95 exceeds budgets in CI or field telemetry.
- **Thermal/IO constraints:** on mobile, monitor thermals and adapt sample rates/model sizes; on desktops, pin capture/decoding threads to dedicated cores to minimize jitter.
- **Model profiling:** maintain profiler presets (CPU/GPU traces, memory snapshots) and attach perf baselines to each model version; reject promotions that regress real-time factors.
- **Hardware guidance:** publish a sizing matrix (RAM/CPU/GPU/network) for expected meeting sizes and noise environments; detect underpowered devices and auto-enable lightweight pipelines.

## Customer Support and Feedback Loops
- **In-app feedback:** provide a “report issue” flow that captures anonymized logs/metrics (with opt-in) plus a short audio excerpt when users flag transcription/voice errors; pre-redact PII before upload.
- **Support SLAs:** define response/resolution targets by severity; integrate on-call rotation details and escalation paths into the runbook.
- **Feedback-driven evals:** channel user-marked “wrong transcript” or “bad TTS pronunciation” clips into a curated evaluation queue with reviewer guidelines and auto-linked build/policy versions.
- **Crash/health reports:** collect crash dumps and watchdog resets locally; if user opts in, upload minimal stacks plus device profile to prioritize fixes, respecting air-gapped/managed policies.

## Alternatives
- Cross-platform via **Electron + Node** with Python backend if web tech is preferred.
- Mobile option: reuse Python service in the cloud; Android app in Kotlin streams audio via WebRTC to backend.
