package com.meetingassistant.audio;

import javax.sound.sampled.*;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Audio capture service using Java Sound API.
 * Captures microphone input, applies VAD, and feeds audio chunks to callbacks.
 */
public class CaptureService {
    private final VadGate vadGate = new VadGate();
    private TargetDataLine audioLine;
    private final AtomicBoolean isCapturing = new AtomicBoolean(false);
    private Thread captureThread;
    private final List<AudioChunkListener> chunkListeners = new ArrayList<>();
    private final ByteArrayOutputStream audioBuffer = new ByteArrayOutputStream();
    
    // Audio format: 16kHz, 16-bit, mono (suitable for speech recognition)
    private static final AudioFormat AUDIO_FORMAT = new AudioFormat(
        16000.0f,  // Sample rate
        16,        // Sample size in bits
        1,         // Channels (mono)
        true,      // Signed
        false      // Little endian
    );
    
    public interface AudioChunkListener {
        void onAudioChunk(byte[] audioData, int sampleRate);
    }
    
    public CaptureService() {
        vadGate.setSilenceThreshold(-42.0);
    }
    
    public void attachVadGate() {
        vadGate.setSilenceThreshold(-42.0);
    }
    
    public void addChunkListener(AudioChunkListener listener) {
        synchronized (chunkListeners) {
            chunkListeners.add(listener);
        }
    }
    
    public void removeChunkListener(AudioChunkListener listener) {
        synchronized (chunkListeners) {
            chunkListeners.remove(listener);
        }
    }
    
    /**
     * Lists available audio input devices.
     */
    public static List<Mixer.Info> listInputDevices() {
        List<Mixer.Info> devices = new ArrayList<>();
        Mixer.Info[] mixers = AudioSystem.getMixerInfo();
        
        for (Mixer.Info mixerInfo : mixers) {
            Mixer mixer = AudioSystem.getMixer(mixerInfo);
            Line.Info[] lineInfos = mixer.getTargetLineInfo();
            if (lineInfos.length > 0) {
                devices.add(mixerInfo);
            }
        }
        return devices;
    }
    
    /**
     * Starts audio capture from the default microphone.
     */
    public void startCapture() throws LineUnavailableException {
        startCapture(null);
    }
    
    /**
     * Starts audio capture from a specific mixer.
     */
    public void startCapture(Mixer.Info mixerInfo) throws LineUnavailableException {
        if (isCapturing.get()) {
            stopCapture();
        }
        
        DataLine.Info info = new DataLine.Info(TargetDataLine.class, AUDIO_FORMAT);
        TargetDataLine line;
        
        if (mixerInfo != null) {
            Mixer mixer = AudioSystem.getMixer(mixerInfo);
            line = (TargetDataLine) mixer.getLine(info);
        } else {
            line = (TargetDataLine) AudioSystem.getLine(info);
        }
        
        line.open(AUDIO_FORMAT);
        this.audioLine = line;
        
        isCapturing.set(true);
        audioLine.start();
        
        captureThread = new Thread(this::captureLoop, "AudioCapture");
        captureThread.setDaemon(true);
        captureThread.start();
    }
    
    /**
     * Stops audio capture.
     */
    public void stopCapture() {
        isCapturing.set(false);
        
        if (audioLine != null) {
            audioLine.stop();
            audioLine.close();
            audioLine = null;
        }
        
        if (captureThread != null) {
            try {
                captureThread.join(1000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            captureThread = null;
        }
        
        synchronized (audioBuffer) {
            audioBuffer.reset();
        }
    }
    
    /**
     * Main capture loop that reads audio data and applies VAD.
     */
    private void captureLoop() {
        byte[] buffer = new byte[1600]; // 100ms at 16kHz, 16-bit mono
        int consecutiveSilentFrames = 0;
        final int SILENT_FRAMES_THRESHOLD = 5; // ~500ms of silence
        
        while (isCapturing.get() && audioLine != null) {
            try {
                int bytesRead = audioLine.read(buffer, 0, buffer.length);
                
                if (bytesRead > 0) {
                    // Apply VAD
                    boolean isSpeech = vadGate.isSpeechFrame(buffer, bytesRead);
                    
                    if (isSpeech) {
                        consecutiveSilentFrames = 0;
                        synchronized (audioBuffer) {
                            audioBuffer.write(buffer, 0, bytesRead);
                        }
                    } else {
                        consecutiveSilentFrames++;
                        
                        // If we have buffered audio and detected silence, flush it
                        synchronized (audioBuffer) {
                            if (audioBuffer.size() > 0 && consecutiveSilentFrames >= SILENT_FRAMES_THRESHOLD) {
                                byte[] chunk = audioBuffer.toByteArray();
                                audioBuffer.reset();
                                
                                // Notify listeners
                                notifyChunkListeners(chunk, (int) AUDIO_FORMAT.getSampleRate());
                            }
                        }
                    }
                }
            } catch (Exception e) {
                System.err.println("Error in capture loop: " + e.getMessage());
                e.printStackTrace();
                break;
            }
        }
        
        // Flush remaining audio on stop
        synchronized (audioBuffer) {
            if (audioBuffer.size() > 0) {
                byte[] chunk = audioBuffer.toByteArray();
                audioBuffer.reset();
                notifyChunkListeners(chunk, (int) AUDIO_FORMAT.getSampleRate());
            }
        }
    }
    
    private void notifyChunkListeners(byte[] audioData, int sampleRate) {
        synchronized (chunkListeners) {
            for (AudioChunkListener listener : chunkListeners) {
                try {
                    listener.onAudioChunk(audioData, sampleRate);
                } catch (Exception e) {
                    System.err.println("Error notifying chunk listener: " + e.getMessage());
                }
            }
        }
    }
    
    public boolean isCapturing() {
        return isCapturing.get();
    }
    
    public AudioFormat getAudioFormat() {
        return AUDIO_FORMAT;
    }
}
