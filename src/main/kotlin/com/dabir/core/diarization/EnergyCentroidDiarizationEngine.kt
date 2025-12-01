package com.dabir.core.diarization

import com.dabir.core.audio.AudioFrame
import kotlin.math.sqrt

/**
 * A lightweight in-memory diarization engine that clusters speakers using simple energy-centric embeddings.
 * This is a placeholder for a production-grade embedding extractor (e.g., ECAPA-TDNN via ONNX Runtime).
 */
class EnergyCentroidDiarizationEngine(
    private val similarityThreshold: Double = 0.85
) : DiarizationEngine {
    private val speakerEmbeddings = mutableMapOf<String, FloatArray>()

    override fun identify(chunk: List<AudioFrame>): String? {
        val embedding = embeddingFor(chunk)
        if (embedding.isEmpty()) return null
        val (bestId, bestScore) = speakerEmbeddings
            .mapValues { (_, stored) -> cosineSimilarity(stored, embedding) }
            .maxByOrNull { it.value } ?: return null
        return if (bestScore >= similarityThreshold) bestId else null
    }

    override fun enroll(speakerId: String, chunk: List<AudioFrame>) {
        val embedding = embeddingFor(chunk)
        if (embedding.isEmpty()) return
        val current = speakerEmbeddings[speakerId]
        speakerEmbeddings[speakerId] = if (current == null) embedding else blend(current, embedding)
    }

    private fun embeddingFor(chunk: List<AudioFrame>): FloatArray {
        if (chunk.isEmpty()) return floatArrayOf()
        val amplitudes = chunk.flatMap { frame -> frame.data.map { it.toInt() } }
        if (amplitudes.isEmpty()) return floatArrayOf()
        val mean = amplitudes.average()
        val rms = sqrt(amplitudes.map { (it - mean) * (it - mean) }.average())
        val max = amplitudes.maxOf { kotlin.math.abs(it) }.toDouble()
        return floatArrayOf(mean.toFloat(), rms.toFloat(), max.toFloat())
    }

    private fun cosineSimilarity(a: FloatArray, b: FloatArray): Double {
        if (a.isEmpty() || b.isEmpty() || a.size != b.size) return -1.0
        val dot = a.indices.sumOf { (a[it] * b[it]).toDouble() }
        val normA = sqrt(a.sumOf { (it * it).toDouble() })
        val normB = sqrt(b.sumOf { (it * it).toDouble() })
        if (normA == 0.0 || normB == 0.0) return -1.0
        return dot / (normA * normB)
    }

    private fun blend(existing: FloatArray, incoming: FloatArray): FloatArray {
        val blended = FloatArray(existing.size)
        for (i in blended.indices) {
            blended[i] = (existing[i] * 0.7f) + (incoming[i] * 0.3f)
        }
        return blended
    }
}
