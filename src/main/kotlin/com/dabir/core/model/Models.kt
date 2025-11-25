package com.dabir.core.model

data class Utterance(
    val id: String,
    val speakerId: String,
    val text: String,
    val startTimeMs: Long,
    val endTimeMs: Long
)

data class Speaker(
    val id: String,
    val displayName: String,
    val embeddings: FloatArray? = null,
    val enrollmentClips: List<String> = emptyList()
)

data class Summary(
    val highlights: List<String> = emptyList(),
    val actionItems: List<String> = emptyList(),
    val decisions: List<String> = emptyList()
)

data class TranscriptExport(
    val utterances: List<Utterance>,
    val speakers: List<Speaker>,
    val metadata: Map<String, String> = emptyMap()
)
