package com.dabir.core.audio

/** Simple value object for PCM audio buffers. */
data class AudioFrame(val data: ShortArray, val sampleRate: Int)

/** Hook for platform capture implementations. */
interface AudioCaptureService {
    fun start(onFrame: (AudioFrame) -> Unit)
    fun stop()
}

/** Noise suppression placeholder. */
interface NoiseSuppressor {
    fun denoise(frame: AudioFrame): AudioFrame
}

/** Voice activity detection contract. */
interface VoiceActivityDetector {
    fun isSpeech(frame: AudioFrame): Boolean
}
