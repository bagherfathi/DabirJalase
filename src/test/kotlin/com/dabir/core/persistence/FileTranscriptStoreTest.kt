package com.dabir.core.persistence

import com.dabir.core.model.Speaker
import com.dabir.core.model.Summary
import com.dabir.core.model.TranscriptExport
import com.dabir.core.model.Utterance
import kotlin.io.path.createTempDirectory
import kotlin.io.path.exists
import kotlin.io.path.readText
import kotlin.test.Test
import kotlin.test.assertTrue

class FileTranscriptStoreTest {
    @Test
    fun `writes timestamped markdown and json`() {
        val tempDir = createTempDirectory("transcripts-")
        val store = FileTranscriptStore(tempDir)
        val export = TranscriptExport(
            utterances = listOf(Utterance("1", "spk1", "سلام دنیا", 0, 1000)),
            speakers = listOf(Speaker("spk1", "Speaker 1")),
            metadata = mapOf("meetingId" to "demo")
        )
        val summary = Summary(highlights = listOf("سلام"))

        val jsonPath = store.save(export, summary)
        val mdPath = jsonPath.resolveSibling(jsonPath.fileName.toString().replace(".json", ".md"))

        assertTrue(jsonPath.exists(), "JSON file should be created")
        assertTrue(mdPath.exists(), "Markdown file should be created")

        val jsonBody = jsonPath.readText()
        val mdBody = mdPath.readText()
        assertTrue(jsonBody.contains("meetingId"))
        assertTrue(mdBody.contains("## خلاصه"))
    }
}
