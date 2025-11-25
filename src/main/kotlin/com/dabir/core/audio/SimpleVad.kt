package com.dabir.core.audio

/**
 * Lightweight placeholder VAD that marks speech based on average absolute amplitude.
 * Replace with Silero ONNX in production.
 */
class SimpleVad(private val amplitudeThreshold: Int = 500) : VoiceActivityDetector {
    override fun isSpeech(frame: AudioFrame): Boolean {
        if (frame.data.isEmpty()) return false
        val avgAmplitude = frame.data.map { kotlin.math.abs(it.toInt()) }.average()
        return avgAmplitude >= amplitudeThreshold
    }
}
