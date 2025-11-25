package com.dabir.core.export

import com.dabir.core.model.Summary
import com.dabir.core.model.TranscriptExport

object TranscriptExporter {
    fun toMarkdown(export: TranscriptExport, summary: Summary? = null): String {
        val builder = StringBuilder()
        builder.appendLine("# گفتگو")
        builder.appendLine()
        builder.appendLine("## گویندگان")
        export.speakers.forEach { speaker ->
            builder.appendLine("- ${speaker.id}: ${speaker.displayName}")
        }
        builder.appendLine()
        builder.appendLine("## متن")
        export.utterances.forEach { utt ->
            builder.appendLine("- **${utt.speakerId}** [${utt.startTimeMs}-${utt.endTimeMs}ms]: ${utt.text}")
        }
        summary?.let {
            builder.appendLine()
            builder.appendLine("## خلاصه")
            if (it.highlights.isNotEmpty()) {
                builder.appendLine("- نکات کلیدی:")
                it.highlights.forEach { h -> builder.appendLine("  - $h") }
            }
            if (it.actionItems.isNotEmpty()) {
                builder.appendLine("- اقدامات:")
                it.actionItems.forEach { a -> builder.appendLine("  - $a") }
            }
            if (it.decisions.isNotEmpty()) {
                builder.appendLine("- تصمیم‌ها:")
                it.decisions.forEach { d -> builder.appendLine("  - $d") }
            }
        }
        return builder.toString()
    }

    fun toJson(export: TranscriptExport, summary: Summary? = null): String {
        val speakerJson = export.speakers.joinToString(prefix = "[", postfix = "]") { speaker ->
            "{" + "\"id\":\"${speaker.id}\",\"name\":\"${speaker.displayName}\"" + "}"
        }
        val utteranceJson = export.utterances.joinToString(prefix = "[", postfix = "]") { utt ->
            "{" +
                "\"id\":\"${utt.id}\"," +
                "\"speakerId\":\"${utt.speakerId}\"," +
                "\"text\":\"${utt.text.replace("\"", "\\\"")}\"," +
                "\"start\":${utt.startTimeMs}," +
                "\"end\":${utt.endTimeMs}" + "}"
        }
        val summaryJson = summary?.let {
            "\"summary\":{\"highlights\":${it.highlights.toJsonArray()},\"actionItems\":${it.actionItems.toJsonArray()},\"decisions\":${it.decisions.toJsonArray()}}"
        }
        val metadataJson = if (export.metadata.isEmpty()) "{}" else export.metadata.entries.joinToString(prefix = "{", postfix = "}") { entry ->
            "\"${entry.key}\":\"${entry.value}\""
        }
        val base = "\"speakers\":$speakerJson,\"utterances\":$utteranceJson,\"metadata\":$metadataJson"
        return if (summaryJson != null) "{$base,$summaryJson}" else "{$base}"
    }

    private fun List<String>.toJsonArray(): String = joinToString(prefix = "[", postfix = "]") { "\"${it.replace("\"", "\\\"")}\"" }
}
