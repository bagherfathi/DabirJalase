package com.dabir

import com.dabir.core.audio.AudioFrame
import com.dabir.core.audio.PassThroughSuppressor
import com.dabir.core.audio.SimpleVad
import com.dabir.core.conversation.ConversationState
import com.dabir.core.conversation.MeetingPipeline
import com.dabir.core.diarization.EnergyCentroidDiarizationEngine
import com.dabir.core.model.Speaker
import com.dabir.core.stt.WhisperOnnxStub
import com.dabir.core.summarization.KeywordSummarizer
import com.dabir.core.tts.StubTtsEngine
import com.dabir.core.export.TranscriptExporter
import com.dabir.core.persistence.FileTranscriptStore
import java.nio.file.Paths

/**
 * Simple console demo that feeds synthetic frames through the meeting pipeline.
 */
fun main() {
    val conversationState = ConversationState()
    val pipeline = MeetingPipeline(
        vad = SimpleVad(amplitudeThreshold = 100),
        noiseSuppressor = PassThroughSuppressor(),
        stt = WhisperOnnxStub(),
        diarization = EnergyCentroidDiarizationEngine(similarityThreshold = 0.90),
        conversationState = conversationState,
        summarizer = KeywordSummarizer(),
        tts = StubTtsEngine()
    )

    val fakeFrames = listOf(
        AudioFrame(shortArrayOf(50, 80, 120, 90), 16000),
        AudioFrame(shortArrayOf(0, 0, 10, 0), 16000),
        AudioFrame(shortArrayOf(500, 700, 800, 900), 16000),
        AudioFrame(shortArrayOf(0, 0, 0, 0), 16000)
    )

    fakeFrames.forEach { frame ->
        pipeline.ingest(frame) { chunk ->
            println("Unknown speaker detected after ${chunk.size} frames. Asking for name...")
            Speaker(id = "spk-${chunk.size}", displayName = "Guest ${chunk.size}")
        }
    }

    val summary = pipeline.summarize()
    val export = conversationState.snapshot(metadata = mapOf("source" to "demo"))
    val store = FileTranscriptStore(Paths.get("build/transcripts"))
    store.save(export, summary)

    println("\n--- Markdown Export ---\n")
    println(TranscriptExporter.toMarkdown(export, summary))

    println("\n--- JSON Export ---\n")
    println(TranscriptExporter.toJson(export, summary))
}
