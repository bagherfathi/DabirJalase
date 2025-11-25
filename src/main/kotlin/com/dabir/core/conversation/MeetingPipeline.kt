package com.dabir.core.conversation

import com.dabir.core.audio.AudioFrame
import com.dabir.core.audio.NoiseSuppressor
import com.dabir.core.audio.VoiceActivityDetector
import com.dabir.core.diarization.DiarizationEngine
import com.dabir.core.model.Speaker
import com.dabir.core.stt.SttEngine
import com.dabir.core.summarization.Summarizer
import com.dabir.core.tts.TtsEngine
import java.util.concurrent.CopyOnWriteArrayList

class MeetingPipeline(
    private val vad: VoiceActivityDetector,
    private val noiseSuppressor: NoiseSuppressor,
    private val stt: SttEngine,
    private val diarization: DiarizationEngine,
    private val conversationState: ConversationState,
    private val summarizer: Summarizer,
    private val tts: TtsEngine
) {
    private val currentChunk = CopyOnWriteArrayList<AudioFrame>()

    fun ingest(frame: AudioFrame, onUnknownSpeaker: (List<AudioFrame>) -> Speaker) {
        val denoised = noiseSuppressor.denoise(frame)
        if (vad.isSpeech(denoised)) {
            currentChunk += denoised
            return
        }

        if (currentChunk.isEmpty()) return

        val transcript = stt.transcribe(currentChunk.toList())
        val detectedSpeakerId = diarization.identify(currentChunk.toList())
        val speaker = if (detectedSpeakerId != null) {
            conversationState.speaker(detectedSpeakerId)
                ?: onUnknownSpeaker(currentChunk.toList()).also { newSpeaker ->
                    conversationState.registerSpeaker(newSpeaker)
                    diarization.enroll(newSpeaker.id, currentChunk.toList())
                }
        } else {
            onUnknownSpeaker(currentChunk.toList()).also { newSpeaker ->
                conversationState.registerSpeaker(newSpeaker)
                diarization.enroll(newSpeaker.id, currentChunk.toList())
            }
        }

        conversationState.addUtterance(
            speakerId = speaker.id,
            text = transcript.text,
            startTimeMs = transcript.startTimeMs,
            endTimeMs = transcript.endTimeMs
        )

        diarization.enroll(speaker.id, currentChunk.toList())

        currentChunk.clear()
    }

    fun summarize(): com.dabir.core.model.Summary {
        return summarizer.summarize(conversationState.allUtterances())
    }

    fun speak(text: String, voice: String = "default"): ByteArray = tts.synthesize(text, voice)
}
