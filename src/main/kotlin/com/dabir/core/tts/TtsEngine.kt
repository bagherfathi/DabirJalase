package com.dabir.core.tts

interface TtsEngine {
    fun synthesize(text: String, voice: String = "default"): ByteArray
}

class StubTtsEngine : TtsEngine {
    override fun synthesize(text: String, voice: String): ByteArray {
        return ByteArray(0)
    }
}
