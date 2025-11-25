package com.dabir.core.audio

/**
 * Placeholder noise suppressor. Integrate RNNoise/NSNet2 here.
 */
class PassThroughSuppressor : NoiseSuppressor {
    override fun denoise(frame: AudioFrame): AudioFrame = frame
}
