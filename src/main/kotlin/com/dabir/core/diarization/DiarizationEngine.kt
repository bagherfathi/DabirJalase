package com.dabir.core.diarization

import com.dabir.core.audio.AudioFrame

interface DiarizationEngine {
    /** Returns a known speakerId or null if unknown. */
    fun identify(chunk: List<AudioFrame>): String?

    /** Enroll or update a speaker profile using the provided chunk. */
    fun enroll(speakerId: String, chunk: List<AudioFrame>)
}

class StubDiarizationEngine : DiarizationEngine {
    override fun identify(chunk: List<AudioFrame>): String? = null
    override fun enroll(speakerId: String, chunk: List<AudioFrame>) { /* no-op */ }
}
