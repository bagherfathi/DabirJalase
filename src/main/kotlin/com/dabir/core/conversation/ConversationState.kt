package com.dabir.core.conversation

import com.dabir.core.model.Speaker
import com.dabir.core.model.Utterance
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicLong

class ConversationState {
    private val speakers = ConcurrentHashMap<String, Speaker>()
    private val utterances = CopyOnWriteArrayList<Utterance>()
    private val idCounter = AtomicLong(0)

    fun registerSpeaker(speaker: Speaker) {
        speakers[speaker.id] = speaker
    }

    fun registerSpeakers(speakers: Iterable<Speaker>) {
        speakers.forEach { registerSpeaker(it) }
    }

    fun speaker(id: String): Speaker? = speakers[id]

    fun addUtterance(speakerId: String, text: String, startTimeMs: Long, endTimeMs: Long): Utterance {
        val utterance = Utterance(
            id = "utt-${idCounter.incrementAndGet()}",
            speakerId = speakerId,
            text = text,
            startTimeMs = startTimeMs,
            endTimeMs = endTimeMs
        )
        utterances += utterance
        return utterance
    }

    fun allSpeakers(): List<Speaker> = speakers.values.toList()
    fun allUtterances(): List<Utterance> = utterances.toList()

    fun snapshot(metadata: Map<String, String> = emptyMap()): com.dabir.core.model.TranscriptExport {
        return com.dabir.core.model.TranscriptExport(
            utterances = allUtterances(),
            speakers = allSpeakers(),
            metadata = metadata
        )
    }
}
