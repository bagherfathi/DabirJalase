package com.dabir.core.persistence

import com.dabir.core.model.Speaker
import java.nio.file.Files
import java.nio.file.Path
import java.util.stream.Collectors

interface SpeakerStore {
    fun save(speakers: List<Speaker>): Path
    fun load(): List<Speaker>
}

/**
 * Writes speakers to a TSV file for simple, dependency-free persistence. Columns:
 * id, displayName, embeddings (comma-separated floats), enrollmentClips (pipe-separated paths)
 */
class FileSpeakerStore(private val path: Path) : SpeakerStore {
    init {
        if (Files.notExists(path.parent)) {
            Files.createDirectories(path.parent)
        }
        if (Files.notExists(path)) {
            Files.createFile(path)
        }
    }

    override fun save(speakers: List<Speaker>): Path {
        val lines = speakers.map { speaker ->
            listOf(
                speaker.id,
                speaker.displayName,
                speaker.embeddings?.joinToString(",") ?: "",
                speaker.enrollmentClips.joinToString("|")
            ).joinToString(separator = "\t")
        }
        Files.write(path, lines)
        return path
    }

    override fun load(): List<Speaker> {
        if (Files.size(path) == 0L) return emptyList()
        return Files.lines(path).use { stream ->
            stream.filter { it.isNotBlank() }
                .map { line ->
                    val parts = line.split('\t')
                    val id = parts.getOrElse(0) { "" }
                    val name = parts.getOrElse(1) { id }
                    val embeddingsRaw = parts.getOrElse(2) { "" }
                    val embeddings = embeddingsRaw
                        .takeIf { it.isNotBlank() }
                        ?.split(',')
                        ?.mapNotNull { token -> token.toFloatOrNull() }
                        ?.toFloatArray()
                    val clips = parts.getOrElse(3) { "" }
                        .split('|')
                        .filter { it.isNotBlank() }
                    Speaker(id = id, displayName = name, embeddings = embeddings, enrollmentClips = clips)
                }
                .collect(Collectors.toList())
        }
    }
}
