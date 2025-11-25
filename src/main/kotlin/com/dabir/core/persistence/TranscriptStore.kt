package com.dabir.core.persistence

import com.dabir.core.export.TranscriptExporter
import com.dabir.core.model.Summary
import com.dabir.core.model.TranscriptExport
import java.nio.file.Files
import java.nio.file.Path
import java.time.Instant
import java.time.format.DateTimeFormatter

interface TranscriptStore {
    fun save(export: TranscriptExport, summary: Summary? = null): Path
}

/**
 * Minimal file-system backed storage that writes paired Markdown and JSON files
 * for a meeting transcript. File names are timestamped for easy ordering.
 */
class FileTranscriptStore(
    private val root: Path
) : TranscriptStore {
    init {
        if (!Files.exists(root)) {
            Files.createDirectories(root)
        }
    }

    override fun save(export: TranscriptExport, summary: Summary?): Path {
        val timestamp = DateTimeFormatter.ISO_INSTANT.format(Instant.now())
        val sanitizedTs = timestamp.replace(":", "-")
        val baseName = "meeting-$sanitizedTs"
        val jsonPath = root.resolve("$baseName.json")
        val mdPath = root.resolve("$baseName.md")

        Files.writeString(jsonPath, TranscriptExporter.toJson(export, summary))
        Files.writeString(mdPath, TranscriptExporter.toMarkdown(export, summary))

        return jsonPath
    }
}
