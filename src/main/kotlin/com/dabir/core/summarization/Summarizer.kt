package com.dabir.core.summarization

import com.dabir.core.model.Summary
import com.dabir.core.model.Utterance

interface Summarizer {
    fun summarize(utterances: List<Utterance>): Summary
}

class StubSummarizer : Summarizer {
    override fun summarize(utterances: List<Utterance>): Summary {
        return Summary(
            highlights = listOf("[خلاصه نمونه – این بخش را با خروجی LLM جایگزین کنید]"),
            actionItems = emptyList(),
            decisions = emptyList()
        )
    }
}

/**
 * A lightweight heuristic summarizer that extracts recurring phrases and simple action-item cues.
 * Intended for offline smoke tests until an LLM-based summarizer is wired in.
 */
class KeywordSummarizer(
    private val minFrequency: Int = 2,
    private val actionKeywords: Set<String> = setOf("باید", "انجام", "تحویل", "پیگیری")
) : Summarizer {
    override fun summarize(utterances: List<Utterance>): Summary {
        if (utterances.isEmpty()) return Summary()
        val tokens = utterances.flatMap { it.text.split(" ") }.filter { it.isNotBlank() }
        val freq = tokens.groupingBy { it }.eachCount().filter { it.value >= minFrequency }
        val highlights = freq.keys.take(5)

        val actionItems = utterances
            .filter { utt -> actionKeywords.any { keyword -> utt.text.contains(keyword) } }
            .map { utt -> "${utt.speakerId}: ${utt.text}" }

        val decisions = utterances
            .filter { it.text.contains("تصمیم") || it.text.contains("توافق") }
            .map { it.text }

        return Summary(
            highlights = highlights,
            actionItems = actionItems,
            decisions = decisions
        )
    }
}
