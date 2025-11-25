package com.dabir.core.conversation

import com.dabir.core.audio.AudioFrame
import kotlin.math.sqrt

/**
 * Tracks speaker energy levels to identify the main/dominant speaker.
 * Used for focusing UI on the active speaker in noisy environments.
 */
class SpeakerFocusTracker {
    private val speakerEnergies = mutableMapOf<String, SpeakerEnergyStats>()
    private var currentMainSpeaker: String? = null
    
    data class SpeakerEnergyStats(
        var totalEnergy: Double = 0.0,
        var frameCount: Int = 0,
        var recentEnergy: Double = 0.0, // Energy in last few frames
        var peakEnergy: Double = 0.0,
        var lastUpdateTime: Long = System.currentTimeMillis()
    ) {
        val averageEnergy: Double
            get() = if (frameCount > 0) totalEnergy / frameCount else 0.0
    }
    
    /**
     * Update energy statistics for a speaker from audio chunk.
     */
    fun updateSpeakerEnergy(speakerId: String, audioChunk: List<AudioFrame>) {
        val energy = calculateEnergy(audioChunk)
        val stats = speakerEnergies.getOrPut(speakerId) { SpeakerEnergyStats() }
        
        stats.totalEnergy += energy
        stats.frameCount++
        stats.recentEnergy = (stats.recentEnergy * 0.7) + (energy * 0.3) // Exponential moving average
        stats.peakEnergy = maxOf(stats.peakEnergy, energy)
        stats.lastUpdateTime = System.currentTimeMillis()
    }
    
    /**
     * Calculate RMS energy from audio frames.
     */
    private fun calculateEnergy(frames: List<AudioFrame>): Double {
        if (frames.isEmpty()) return 0.0
        
        var sumSquares = 0.0
        var sampleCount = 0
        
        for (frame in frames) {
            for (sample in frame.data) {
                val normalized = sample / 32768.0
                sumSquares += normalized * normalized
                sampleCount++
            }
        }
        
        if (sampleCount == 0) return 0.0
        
        val rms = sqrt(sumSquares / sampleCount)
        return rms
    }
    
    /**
     * Get the main/dominant speaker based on recent energy and activity.
     */
    fun getMainSpeaker(): String? {
        if (speakerEnergies.isEmpty()) return null
        
        val now = System.currentTimeMillis()
        val recentThreshold = 5000L // 5 seconds
        
        // Filter out inactive speakers (haven't spoken in last 5 seconds)
        val activeSpeakers = speakerEnergies.filter { (_, stats) ->
            now - stats.lastUpdateTime < recentThreshold
        }
        
        if (activeSpeakers.isEmpty()) {
            // If no recent speakers, use overall most energetic
            return speakerEnergies.maxByOrNull { it.value.averageEnergy }?.key
        }
        
        // Find speaker with highest recent energy (weighted by recency)
        val mainSpeaker = activeSpeakers.maxByOrNull { (_, stats) ->
            // Combine recent energy with recency factor
            val recencyFactor = 1.0 - ((now - stats.lastUpdateTime) / recentThreshold.toDouble())
            stats.recentEnergy * (0.7 + 0.3 * recencyFactor)
        }?.key
        
        currentMainSpeaker = mainSpeaker
        return mainSpeaker
    }
    
    /**
     * Get energy level for a specific speaker (0.0 to 1.0).
     */
    fun getSpeakerEnergyLevel(speakerId: String): Double {
        val stats = speakerEnergies[speakerId] ?: return 0.0
        
        // Normalize energy to 0-1 range (assuming max RMS is around 0.3 for speech)
        return (stats.recentEnergy / 0.3).coerceIn(0.0, 1.0)
    }
    
    /**
     * Get all speakers sorted by energy level (most energetic first).
     */
    fun getSpeakersByEnergy(): List<Pair<String, Double>> {
        return speakerEnergies.map { (id, stats) ->
            id to stats.recentEnergy
        }.sortedByDescending { it.second }
    }
    
    /**
     * Check if a speaker is currently active (speaking).
     */
    fun isSpeakerActive(speakerId: String, threshold: Double = 0.01): Boolean {
        val stats = speakerEnergies[speakerId] ?: return false
        val now = System.currentTimeMillis()
        val recentThreshold = 3000L // 3 seconds
        
        return (now - stats.lastUpdateTime < recentThreshold) && 
               stats.recentEnergy > threshold
    }
    
    /**
     * Reset statistics for a speaker.
     */
    fun resetSpeaker(speakerId: String) {
        speakerEnergies.remove(speakerId)
        if (currentMainSpeaker == speakerId) {
            currentMainSpeaker = null
        }
    }
    
    /**
     * Clear all statistics.
     */
    fun clear() {
        speakerEnergies.clear()
        currentMainSpeaker = null
    }
    
    /**
     * Get current main speaker (cached).
     */
    fun getCurrentMainSpeaker(): String? = currentMainSpeaker
}

