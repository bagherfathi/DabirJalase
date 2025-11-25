package com.dabir.core

import com.dabir.core.audio.AudioFrame
import com.dabir.core.diarization.EnergyCentroidDiarizationEngine
import com.dabir.core.export.TranscriptExporter
import com.dabir.core.model.Speaker
import com.dabir.core.model.TranscriptExport
import com.dabir.core.model.Utterance
import com.dabir.core.summarization.KeywordSummarizer
import kotlin.test.Test
import kotlin.test.assertTrue

class CoreSmokeTests {
    @Test
    fun `diarization separates low and high energy speakers`() {
        val engine = EnergyCentroidDiarizationEngine(similarityThreshold = 0.75)
        val loudChunk = listOf(AudioFrame(shortArrayOf(900, 800, 950, 970), 16000))
        val softChunk = listOf(AudioFrame(shortArrayOf(80, 70, 60, 75), 16000))

        engine.enroll("loud", loudChunk)
        engine.enroll("soft", softChunk)

        val predictedLoud = engine.identify(loudChunk)
        val predictedSoft = engine.identify(softChunk)

        assertTrue(predictedLoud == "loud" && predictedSoft == "soft")
    }

    @Test
    fun `summarizer and exporter produce bullet points`() {
        val summarizer = KeywordSummarizer(minFrequency = 1, actionKeywords = setOf("انجام"))
        val utterances = listOf(
            Utterance("1", "alice", "باید کار را انجام دهیم", 0, 1000),
            Utterance("2", "bob", "تصمیم گرفته شد", 1000, 2000)
        )
        val summary = summarizer.summarize(utterances)
        val export = TranscriptExport(utterances, listOf(Speaker("alice", "Alice"), Speaker("bob", "Bob")))
        val markdown = TranscriptExporter.toMarkdown(export, summary)

        assertTrue(markdown.contains("## خلاصه"))
        assertTrue(summary.actionItems.isNotEmpty())
        assertTrue(summary.decisions.isNotEmpty())
    }
}
