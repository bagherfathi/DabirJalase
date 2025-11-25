package com.meetingassistant.audio;

/**
 * Minimal VAD placeholder. Replace with on-device model or WebRTC VAD wrapper.
 */
public class VadGate {
    private double silenceThresholdDb = -40.0;

    public void setSilenceThreshold(double thresholdDb) {
        this.silenceThresholdDb = thresholdDb;
    }

    public boolean isSpeechFrame(byte[] pcmBytes) {
        // TODO: implement real VAD check. This always returns true to keep the stream flowing in the scaffold.
        return true;
    }

    public double getSilenceThresholdDb() {
        return silenceThresholdDb;
    }
}
