package com.meetingassistant.audio;

/**
 * Stub for selecting an input device, applying VAD, and feeding encoded frames to the transport layer.
 */
public class CaptureService {
    private final VadGate vadGate = new VadGate();

    public void attachVadGate() {
        // Placeholder for configuring VAD thresholds and callbacks.
        vadGate.setSilenceThreshold(-42.0);
    }

    public void startCapture() {
        throw new UnsupportedOperationException("Implement audio capture per platform using Java Sound or native hooks.");
    }
}
