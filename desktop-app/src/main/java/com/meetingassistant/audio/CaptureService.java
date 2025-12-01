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
        System.out.println("[DEBUG] startCapture() called with mixerInfo: " + (mixerInfo != null ? mixerInfo.getName() : "null"));
        if (isCapturing.get()) {
            System.out.println("[DEBUG] Already capturing, stopping first...");
            stopCapture();
        }
        
        System.out.println("[DEBUG] Requested audio format: " + AUDIO_FORMAT);
        DataLine.Info info = new DataLine.Info(TargetDataLine.class, AUDIO_FORMAT);
        TargetDataLine line = null;
        
        // Try to get the line
        try {
            if (mixerInfo != null) {
                System.out.println("[DEBUG] Trying to get line from specific mixer: " + mixerInfo.getName());
                Mixer mixer = AudioSystem.getMixer(mixerInfo);
                if (mixer.isLineSupported(info)) {
                    System.out.println("[DEBUG] Line is supported by mixer");
                    line = (TargetDataLine) mixer.getLine(info);
                } else {
                    System.out.println("[WARN] Line format not supported by mixer");
                }
            } else {
                System.out.println("[DEBUG] Trying to get line from default system");
                if (AudioSystem.isLineSupported(info)) {
                    System.out.println("[DEBUG] Line format is supported by system");
                    line = (TargetDataLine) AudioSystem.getLine(info);
                } else {
                    System.out.println("[WARN] Line format not supported by system");
                }
            }
        } catch (Exception e) {
            System.err.println("[ERROR] Error getting audio line: " + e.getMessage());
            e.printStackTrace();
        }
        
        // If exact format not supported, try a more common format
        if (line == null) {
            AudioFormat fallbackFormat = new AudioFormat(
                AudioFormat.Encoding.PCM_SIGNED,
                44100.0f,  // Common sample rate
                16,        // 16-bit
                1,         // Mono
                2,         // Frame size
                44100.0f,  // Frame rate
                false      // Little endian
            );
            DataLine.Info fallbackInfo = new DataLine.Info(TargetDataLine.class, fallbackFormat);
            
            try {
                if (mixerInfo != null) {
                    Mixer mixer = AudioSystem.getMixer(mixerInfo);
                    if (mixer.isLineSupported(fallbackInfo)) {
                        line = (TargetDataLine) mixer.getLine(fallbackInfo);
                        System.out.println("Using fallback audio format: 44.1kHz");
                    }
                } else {
                    if (AudioSystem.isLineSupported(fallbackInfo)) {
                        line = (TargetDataLine) AudioSystem.getLine(fallbackInfo);
                        System.out.println("Using fallback audio format: 44.1kHz");
                    }
                }
            } catch (Exception e) {
                System.err.println("Error getting fallback audio line: " + e.getMessage());
            }
        }
        
        if (line == null) {
            throw new LineUnavailableException("No supported audio input line found. Please check your microphone.");
        }
        
        // Get the format that will be used
        AudioFormat formatToUse;
        if (line.getLineInfo() instanceof DataLine.Info) {
            DataLine.Info dataLineInfo = (DataLine.Info) line.getLineInfo();
            AudioFormat[] formats = dataLineInfo.getFormats();
            if (formats != null && formats.length > 0) {
                formatToUse = formats[0];
            } else {
                formatToUse = AUDIO_FORMAT;
            }
        } else {
            formatToUse = AUDIO_FORMAT;
        }
        
        // Ensure frame size is specified
        if (formatToUse.getFrameSize() == AudioSystem.NOT_SPECIFIED) {
            int channels = formatToUse.getChannels();
            int sampleSizeInBits = formatToUse.getSampleSizeInBits();
            if (sampleSizeInBits == AudioSystem.NOT_SPECIFIED) {
                sampleSizeInBits = 16;
            }
            if (channels == AudioSystem.NOT_SPECIFIED) {
                channels = 1;
            }
            float sampleRate = formatToUse.getSampleRate();
            if (sampleRate == AudioSystem.NOT_SPECIFIED) {
                sampleRate = 44100.0f;
            }
            boolean bigEndian = formatToUse.isBigEndian();
            formatToUse = new AudioFormat(
                formatToUse.getEncoding(),
                sampleRate,
                sampleSizeInBits,
                channels,
                channels * (sampleSizeInBits / 8), // frame size
                sampleRate,
                bigEndian
            );
        }
        
        line.open(formatToUse);
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
        System.out.println("[DEBUG] captureLoop started");
        // Calculate buffer size based on actual audio format (100ms of audio)
        AudioFormat actualFormat = audioLine != null ? audioLine.getFormat() : AUDIO_FORMAT;
        int sampleRate = (int) actualFormat.getSampleRate();
        System.out.println("[DEBUG] Audio format: " + actualFormat);
        System.out.println("[DEBUG] Sample rate: " + sampleRate);
        
        // Calculate frame size: channels * (sampleSizeInBits / 8)
        int frameSize = actualFormat.getFrameSize();
        if (frameSize == AudioSystem.NOT_SPECIFIED) {
            // Calculate frame size from format properties
            int channels = actualFormat.getChannels();
            int sampleSizeInBits = actualFormat.getSampleSizeInBits();
            if (sampleSizeInBits == AudioSystem.NOT_SPECIFIED) {
                sampleSizeInBits = 16; // Default to 16-bit
            }
            frameSize = channels * (sampleSizeInBits / 8);
        }
        System.out.println("[DEBUG] Frame size: " + frameSize);
        
        // Buffer size for 100ms of audio: (sampleRate / 10) * frameSize
        int bufferSize = (sampleRate / 10) * frameSize;
        if (bufferSize <= 0) {
            bufferSize = 1600; // fallback: 100ms at 16kHz, 16-bit mono
        }
        System.out.println("[DEBUG] Buffer size: " + bufferSize);
        
        byte[] buffer = new byte[bufferSize];
        int consecutiveSilentFrames = 0;
        final int SILENT_FRAMES_THRESHOLD = 5; // ~500ms of silence
        int totalBytesRead = 0;
        
        System.out.println("[DEBUG] Starting capture loop...");
        while (isCapturing.get() && audioLine != null) {
            try {
                int bytesRead = audioLine.read(buffer, 0, buffer.length);
                
                if (bytesRead > 0) {
                    totalBytesRead += bytesRead;
                    if (totalBytesRead % (sampleRate * frameSize) == 0) { // Log every second
                        System.out.println("[DEBUG] Captured " + (totalBytesRead / (sampleRate * frameSize)) + " seconds of audio");
                    }
                    
                    // Apply VAD
                    boolean isSpeech = vadGate.isSpeechFrame(buffer, bytesRead);
                    
                    if (isSpeech) {
                        consecutiveSilentFrames = 0;
                        synchronized (audioBuffer) {
                            audioBuffer.write(buffer, 0, bytesRead);
                            
                            // Also flush periodically even if speech continues (every 2 seconds)
                            if (audioBuffer.size() > (sampleRate * frameSize * 2)) { // 2 seconds of audio
                                byte[] chunk = audioBuffer.toByteArray();
                                audioBuffer.reset();
                                System.out.println("[DEBUG] Periodic flush (2s): " + chunk.length + " bytes");
                                notifyChunkListeners(chunk, sampleRate);
                            }
                        }
                    } else {
                        consecutiveSilentFrames++;
                        
                        // If we have buffered audio and detected silence, flush it
                        synchronized (audioBuffer) {
                            if (audioBuffer.size() > 0 && consecutiveSilentFrames >= SILENT_FRAMES_THRESHOLD) {
                                byte[] chunk = audioBuffer.toByteArray();
                                audioBuffer.reset();
                                
                                System.out.println("[DEBUG] Flushing audio chunk: " + chunk.length + " bytes");
                                // Notify listeners with actual sample rate
                                notifyChunkListeners(chunk, sampleRate);
                            }
                        }
                    }
                } else if (bytesRead < 0) {
                    System.out.println("[WARN] Negative bytes read: " + bytesRead);
                }
            } catch (Exception e) {
                System.err.println("[ERROR] Error in capture loop: " + e.getMessage());
                e.printStackTrace();
                break;
            }
        }
        
        // Flush remaining audio on stop
        synchronized (audioBuffer) {
            if (audioBuffer.size() > 0) {
                byte[] chunk = audioBuffer.toByteArray();
                audioBuffer.reset();
                notifyChunkListeners(chunk, sampleRate);
            }
        }
    }
    
    private void notifyChunkListeners(byte[] audioData, int sampleRate) {
        synchronized (chunkListeners) {
            System.out.println("[DEBUG] notifyChunkListeners: audioData.length=" + audioData.length + ", listeners=" + chunkListeners.size());
            for (AudioChunkListener listener : chunkListeners) {
                try {
                    listener.onAudioChunk(audioData, sampleRate);
                } catch (Exception e) {
                    System.err.println("[ERROR] Error notifying chunk listener: " + e.getMessage());
                    e.printStackTrace();
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
