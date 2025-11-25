package com.dabir.core.stt

import com.dabir.core.audio.AudioFrame

interface SttEngine {
    data class Transcript(val text: String, val startTimeMs: Long, val endTimeMs: Long)
    fun transcribe(chunk: List<AudioFrame>): Transcript
}

/**
 * Replace this stub with ONNX Runtime Whisper implementation.
 */
class WhisperOnnxStub : SttEngine {
    override fun transcribe(chunk: List<AudioFrame>): SttEngine.Transcript {
        val durationMs = chunk.size * 20L
        val text = "[placeholder transcript in Farsi]"
        return SttEngine.Transcript(text = text, startTimeMs = 0, endTimeMs = durationMs)
    }
}
