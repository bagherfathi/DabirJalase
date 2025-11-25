package com.meetingassistant.audio;

/**
 * Voice Activity Detection (VAD) using energy-based approach.
 * Can be replaced with Silero VAD ONNX model or WebRTC VAD for better accuracy.
 */
public class VadGate {
    private double silenceThresholdDb = -40.0;
    private double energyThreshold = 0.01; // Normalized energy threshold
    private int minSpeechFrames = 3; // Minimum consecutive frames for speech
    
    // For smoothing
    private double[] energyHistory = new double[5];
    private int historyIndex = 0;
    
    public void setSilenceThreshold(double thresholdDb) {
        this.silenceThresholdDb = thresholdDb;
        // Convert dB to linear energy threshold
        this.energyThreshold = Math.pow(10.0, thresholdDb / 20.0);
    }
    
    public void setEnergyThreshold(double threshold) {
        this.energyThreshold = threshold;
    }
    
    public void setMinSpeechFrames(int frames) {
        this.minSpeechFrames = frames;
    }
    
    /**
     * Checks if audio frame contains speech using energy-based VAD.
     * 
     * @param pcmBytes Raw PCM audio data (16-bit samples)
     * @param length Number of bytes to process
     * @return true if speech is detected, false otherwise
     */
    public boolean isSpeechFrame(byte[] pcmBytes, int length) {
        if (length < 2) {
            return false;
        }
        
        // Calculate RMS energy
        double sumSquares = 0.0;
        int sampleCount = length / 2; // 16-bit = 2 bytes per sample
        
        for (int i = 0; i < length - 1; i += 2) {
            // Convert bytes to 16-bit signed integer (little-endian)
            int sample = (pcmBytes[i] & 0xFF) | ((pcmBytes[i + 1] & 0xFF) << 8);
            if (sample > 32767) {
                sample -= 65536; // Convert to signed
            }
            
            // Normalize to [-1, 1]
            double normalized = sample / 32768.0;
            sumSquares += normalized * normalized;
        }
        
        double rms = Math.sqrt(sumSquares / sampleCount);
        
        // Smooth energy using moving average
        energyHistory[historyIndex] = rms;
        historyIndex = (historyIndex + 1) % energyHistory.length;
        
        double avgEnergy = 0.0;
        for (double e : energyHistory) {
            avgEnergy += e;
        }
        avgEnergy /= energyHistory.length;
        
        // Check against threshold
        boolean isSpeech = avgEnergy > energyThreshold;
        
        return isSpeech;
    }
    
    /**
     * Overload for full buffer.
     */
    public boolean isSpeechFrame(byte[] pcmBytes) {
        return isSpeechFrame(pcmBytes, pcmBytes.length);
    }
    
    /**
     * Calculates energy in dB.
     */
    public double calculateEnergyDb(byte[] pcmBytes, int length) {
        if (length < 2) {
            return Double.NEGATIVE_INFINITY;
        }
        
        double sumSquares = 0.0;
        int sampleCount = length / 2;
        
        for (int i = 0; i < length - 1; i += 2) {
            int sample = (pcmBytes[i] & 0xFF) | ((pcmBytes[i + 1] & 0xFF) << 8);
            if (sample > 32767) {
                sample -= 65536;
            }
            double normalized = sample / 32768.0;
            sumSquares += normalized * normalized;
        }
        
        double rms = Math.sqrt(sumSquares / sampleCount);
        return 20.0 * Math.log10(rms + 1e-10); // Add small epsilon to avoid log(0)
    }
    
    public double getSilenceThresholdDb() {
        return silenceThresholdDb;
    }
    
    public double getEnergyThreshold() {
        return energyThreshold;
    }
}
