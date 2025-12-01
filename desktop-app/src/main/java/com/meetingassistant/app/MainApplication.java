package com.meetingassistant.app;

import com.meetingassistant.audio.CaptureService;
import com.meetingassistant.transport.HttpClient;
import com.meetingassistant.ui.ChatTimeline;
import com.meetingassistant.ui.SpeakerPrompt;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.NodeOrientation;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.control.ProgressBar;
import javafx.scene.layout.*;
import javafx.stage.FileChooser;
import javafx.stage.Stage;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import javax.sound.sampled.AudioFormat;

/**
 * Main JavaFX application that integrates all components.
 * Connects audio capture -> HTTP client -> Python services -> UI.
 */
public class MainApplication extends Application {
    private CaptureService captureService;
    private HttpClient httpClient;
    private ChatTimeline chatTimeline;
    private SpeakerPrompt speakerPrompt;
    
    private String currentSessionId;
    private boolean isRecording = false;
    private Map<String, String> speakerNames = new HashMap<>(); // speaker_id -> display_name
    
    private Button startStopButton;
    private Button exportButton;
    private Button playAudioButton;
    private Label statusLabel;
    private ProgressBar audioLevelIndicator;
    private Label audioLevelLabel;
    private List<byte[]> capturedAudioChunks = new ArrayList<>();
    private AudioFormat capturedAudioFormat;
    
    @Override
    public void start(Stage primaryStage) {
        // Initialize components
        captureService = new CaptureService();
        
        // Get server URL from environment variable or system property, default to localhost
        String serverUrl = System.getenv("MEETING_ASSISTANT_SERVER_URL");
        if (serverUrl == null || serverUrl.isEmpty()) {
            serverUrl = System.getProperty("meeting.assistant.server.url");
        }
        if (serverUrl == null || serverUrl.isEmpty()) {
            serverUrl = "http://localhost:8000";
        }
        // Ensure URL doesn't end with /
        if (serverUrl.endsWith("/")) {
            serverUrl = serverUrl.substring(0, serverUrl.length() - 1);
        }
        
        System.out.println("[INFO] Connecting to server: " + serverUrl);
        httpClient = new HttpClient(serverUrl);
        chatTimeline = new ChatTimeline();
        speakerPrompt = new SpeakerPrompt();
        
        // Create UI
        BorderPane root = new BorderPane();
        root.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
        
        // Top: Controls
        HBox controlsBox = new HBox(10);
        controlsBox.setPadding(new Insets(10));
        controlsBox.setAlignment(Pos.CENTER);
        controlsBox.setStyle("-fx-background-color: #e0e0e0;");
        
        startStopButton = new Button("شروع ضبط");
        startStopButton.setStyle("-fx-font-size: 14px; -fx-padding: 8px 16px;");
        startStopButton.setOnAction(e -> toggleRecording());
        
        exportButton = new Button("خروجی خلاصه");
        exportButton.setStyle("-fx-font-size: 14px; -fx-padding: 8px 16px;");
        exportButton.setDisable(true);
        exportButton.setOnAction(e -> exportSummary());
        
        playAudioButton = new Button("▶ پخش صدا");
        playAudioButton.setStyle("-fx-font-size: 14px; -fx-padding: 8px 16px;");
        playAudioButton.setDisable(true);
        playAudioButton.setOnAction(e -> playCapturedAudio());
        
        statusLabel = new Label("آماده");
        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px;");
        
        // Audio level indicator
        audioLevelIndicator = new ProgressBar(0.0);
        audioLevelIndicator.setPrefWidth(200);
        audioLevelIndicator.setPrefHeight(20);
        audioLevelIndicator.setStyle("-fx-accent: green;");
        
        audioLevelLabel = new Label("صدا: --");
        audioLevelLabel.setStyle("-fx-font-size: 11px; -fx-padding: 4px;");
        
        controlsBox.getChildren().addAll(startStopButton, exportButton, playAudioButton, statusLabel, audioLevelIndicator, audioLevelLabel);
        root.setTop(controlsBox);
        
        // Center: Chat timeline
        ScrollPane timelineScroll = chatTimeline.getView();
        root.setCenter(timelineScroll);
        
        // Setup audio capture listener
        captureService.addChunkListener((audioData, sampleRate) -> {
            System.out.println("[DEBUG] Listener callback: audioData.length=" + audioData.length + ", currentSessionId=" + currentSessionId + ", isRecording=" + isRecording);
            
            // Store audio format for playback
            if (capturedAudioFormat == null) {
                capturedAudioFormat = captureService.getAudioFormat();
            }
            
            // Store captured audio for playback
            if (isRecording) {
                synchronized (capturedAudioChunks) {
                    capturedAudioChunks.add(audioData.clone());
                    Platform.runLater(() -> {
                        playAudioButton.setDisable(capturedAudioChunks.isEmpty());
                    });
                }
            }
            
            // Calculate audio level for visual feedback
            calculateAndDisplayAudioLevel(audioData);
            
            if (currentSessionId != null && isRecording) {
                System.out.println("[DEBUG] Calling handleAudioChunk...");
                handleAudioChunk(audioData, sampleRate);
            } else {
                System.out.println("[WARN] Skipping handleAudioChunk - currentSessionId=" + currentSessionId + ", isRecording=" + isRecording);
            }
        });
        
        // Check service health on startup
        checkServiceHealth();
        
        // Setup scene
        Scene scene = new Scene(root, 900, 700);
        primaryStage.setTitle("دبیر جلسه - Meeting Assistant");
        primaryStage.setScene(scene);
        primaryStage.show();
    }
    
    private void checkServiceHealth() {
        httpClient.health().thenAccept(result -> {
            Platform.runLater(() -> {
                if (result != null && "ok".equals(result.get("status"))) {
                    statusLabel.setText("سرویس آماده است");
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: green;");
                } else {
                    statusLabel.setText("خطا در اتصال به سرویس");
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
                }
            });
        }).exceptionally(e -> {
            Platform.runLater(() -> {
                statusLabel.setText("سرویس در دسترس نیست");
                statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
            });
            return null;
        });
    }
    
    private void toggleRecording() {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    }
    
    private void startRecording() {
        System.out.println("[DEBUG] startRecording() called");
        try {
            statusLabel.setText("در حال ایجاد session...");
            statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: blue;");
            System.out.println("[DEBUG] Status updated: Creating session...");
            
            // Create new session
            currentSessionId = UUID.randomUUID().toString();
            String title = "جلسه " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
            System.out.println("[DEBUG] Session ID: " + currentSessionId);
            System.out.println("[DEBUG] Calling httpClient.createSession()...");
            
            httpClient.createSession(currentSessionId, "fa", title).thenAccept(session -> {
                System.out.println("[DEBUG] createSession callback received");
                System.out.println("[DEBUG] Session response: " + (session != null ? session.toString() : "null"));
                
                Platform.runLater(() -> {
                    if (session == null) {
                        System.out.println("[ERROR] Session is null!");
                        statusLabel.setText("خطا: session ایجاد نشد");
                        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
                        return;
                    }
                    
                    System.out.println("[DEBUG] Session created successfully, starting audio capture...");
                    statusLabel.setText("در حال شروع ضبط صدا...");
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: blue;");
                    
                    // Start audio capture
                    try {
                        System.out.println("[DEBUG] Calling captureService.startCapture()...");
                        captureService.startCapture();
                        System.out.println("[DEBUG] captureService.startCapture() completed successfully");
                        
                        // If we get here, capture started successfully
                        isRecording = true;
                        startStopButton.setText("توقف ضبط");
                        exportButton.setDisable(false);
                    statusLabel.setText("در حال ضبط...");
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: green;");
                    chatTimeline.clear();
                    speakerNames.clear();
                    // Clear previous audio chunks
                    synchronized (capturedAudioChunks) {
                        capturedAudioChunks.clear();
                        playAudioButton.setDisable(true);
                    }
                    System.out.println("[DEBUG] Recording started successfully! isRecording=" + isRecording);
                    } catch (javax.sound.sampled.LineUnavailableException e) {
                        System.err.println("[ERROR] LineUnavailableException: " + e.getMessage());
                        e.printStackTrace();
                        String errorMsg = "خطا در دسترسی به میکروفون: " + e.getMessage();
                        if (e.getMessage() != null && e.getMessage().contains("format")) {
                            errorMsg = "فرمت صوتی پشتیبانی نمی‌شود. لطفا میکروفون دیگری امتحان کنید.";
                        }
                        statusLabel.setText(errorMsg);
                        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
                        isRecording = false;
                        startStopButton.setText("شروع ضبط");
                        exportButton.setDisable(true);
                    } catch (Exception e) {
                        System.err.println("[ERROR] Exception in startCapture: " + e.getMessage());
                        e.printStackTrace();
                        String errorMsg = "خطا در شروع ضبط: " + (e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName());
                        statusLabel.setText(errorMsg);
                        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
                        isRecording = false;
                        startStopButton.setText("شروع ضبط");
                        exportButton.setDisable(true);
                    }
                });
            }).exceptionally(e -> {
                System.err.println("[ERROR] Exception in createSession: " + (e != null ? e.getMessage() : "null"));
                if (e != null) {
                    e.printStackTrace();
                }
                Platform.runLater(() -> {
                    String errorMsg = "خطا در ایجاد session: ";
                    if (e != null && e.getCause() != null) {
                        errorMsg += e.getCause().getMessage();
                    } else if (e != null) {
                        errorMsg += e.getMessage();
                    } else {
                        errorMsg += "خطای نامشخص";
                    }
                    statusLabel.setText(errorMsg);
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
                    isRecording = false;
                    startStopButton.setText("شروع ضبط");
                });
                return null;
            });
        } catch (Exception e) {
            System.err.println("[ERROR] Exception in startRecording: " + e.getMessage());
            e.printStackTrace();
            statusLabel.setText("خطا: " + (e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName()));
            statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
        }
    }
    
    private void stopRecording() {
        isRecording = false;
        captureService.stopCapture();
        startStopButton.setText("شروع ضبط");
        statusLabel.setText("ضبط متوقف شد");
        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px;");
        audioLevelIndicator.setProgress(0.0);
        audioLevelLabel.setText("صدا: --");
        // Enable play button if we have captured audio
        synchronized (capturedAudioChunks) {
            playAudioButton.setDisable(capturedAudioChunks.isEmpty());
        }
    }
    
    private void playCapturedAudio() {
        synchronized (capturedAudioChunks) {
            if (capturedAudioChunks.isEmpty()) {
                statusLabel.setText("هیچ صدایی ضبط نشده است");
                return;
            }
        }
        
        statusLabel.setText("در حال پخش...");
        playAudioButton.setDisable(true);
        
        // Play audio in a separate thread
        new Thread(() -> {
            try {
                if (capturedAudioFormat == null) {
                    Platform.runLater(() -> {
                        statusLabel.setText("خطا: فرمت صوتی مشخص نیست");
                        playAudioButton.setDisable(false);
                    });
                    return;
                }
                
                // Combine all audio chunks
                int totalSize = 0;
                synchronized (capturedAudioChunks) {
                    for (byte[] chunk : capturedAudioChunks) {
                        totalSize += chunk.length;
                    }
                }
                
                byte[] combinedAudio = new byte[totalSize];
                int offset = 0;
                synchronized (capturedAudioChunks) {
                    for (byte[] chunk : capturedAudioChunks) {
                        System.arraycopy(chunk, 0, combinedAudio, offset, chunk.length);
                        offset += chunk.length;
                    }
                }
                
                System.out.println("[DEBUG] Playing " + combinedAudio.length + " bytes of audio");
                
                // Get a source data line for playback
                javax.sound.sampled.DataLine.Info info = new javax.sound.sampled.DataLine.Info(
                    javax.sound.sampled.SourceDataLine.class, 
                    capturedAudioFormat
                );
                
                if (!javax.sound.sampled.AudioSystem.isLineSupported(info)) {
                    Platform.runLater(() -> {
                        statusLabel.setText("خطا: فرمت صوتی پشتیبانی نمی‌شود");
                        playAudioButton.setDisable(false);
                    });
                    return;
                }
                
                javax.sound.sampled.SourceDataLine line = (javax.sound.sampled.SourceDataLine) 
                    javax.sound.sampled.AudioSystem.getLine(info);
                line.open(capturedAudioFormat);
                line.start();
                
                // Write audio data in chunks
                int chunkSize = (int) (capturedAudioFormat.getSampleRate() * capturedAudioFormat.getFrameSize() * 0.1); // 100ms chunks
                int bytesWritten = 0;
                while (bytesWritten < combinedAudio.length) {
                    int toWrite = Math.min(chunkSize, combinedAudio.length - bytesWritten);
                    int written = line.write(combinedAudio, bytesWritten, toWrite);
                    bytesWritten += written;
                }
                
                // Wait for playback to finish
                line.drain();
                line.stop();
                line.close();
                
                Platform.runLater(() -> {
                    statusLabel.setText("پخش کامل شد");
                    playAudioButton.setDisable(false);
                });
                
            } catch (Exception e) {
                System.err.println("[ERROR] Error playing audio: " + e.getMessage());
                e.printStackTrace();
                Platform.runLater(() -> {
                    statusLabel.setText("خطا در پخش: " + e.getMessage());
                    playAudioButton.setDisable(false);
                });
            }
        }, "AudioPlayback").start();
    }
    
    private void calculateAndDisplayAudioLevel(byte[] audioData) {
        // Calculate RMS (Root Mean Square) for audio level
        long sum = 0;
        int sampleCount = 0;
        
        // Convert bytes to samples and calculate RMS
        for (int i = 0; i < audioData.length - 1; i += 2) {
            int sample = (audioData[i] & 0xFF) | ((audioData[i + 1] & 0xFF) << 8);
            if (sample > 32767) {
                sample -= 65536;
            }
            sum += (long) sample * sample;
            sampleCount++;
        }
        
        if (sampleCount > 0) {
            double rms = Math.sqrt(sum / (double) sampleCount);
            double normalizedLevel = Math.min(rms / 32768.0, 1.0); // Normalize to 0-1
            
            Platform.runLater(() -> {
                audioLevelIndicator.setProgress(normalizedLevel);
                
                // Display as percentage
                int percentage = (int) (normalizedLevel * 100);
                if (percentage < 5) {
                    audioLevelLabel.setText("صدا: خاموش");
                    audioLevelLabel.setStyle("-fx-font-size: 11px; -fx-padding: 4px; -fx-text-fill: gray;");
                } else if (percentage < 20) {
                    audioLevelLabel.setText("صدا: ضعیف (" + percentage + "%)");
                    audioLevelLabel.setStyle("-fx-font-size: 11px; -fx-padding: 4px; -fx-text-fill: orange;");
                } else {
                    audioLevelLabel.setText("صدا: فعال (" + percentage + "%)");
                    audioLevelLabel.setStyle("-fx-font-size: 11px; -fx-padding: 4px; -fx-text-fill: green;");
                }
            });
        }
    }
    
    private void handleAudioChunk(byte[] audioData, int sampleRate) {
        if (currentSessionId == null) {
            System.out.println("[WARN] handleAudioChunk called but currentSessionId is null");
            return;
        }
        
        System.out.println("[DEBUG] handleAudioChunk: audioData.length=" + audioData.length + ", sampleRate=" + sampleRate);
        System.out.println("[DEBUG] Calling httpClient.ingestAudio() for session: " + currentSessionId);
        
        // Update status to show we're processing
        Platform.runLater(() -> {
            statusLabel.setText("در حال پردازش صدا...");
        });
        
        httpClient.ingestAudio(currentSessionId, audioData, sampleRate).thenAccept(response -> {
            System.out.println("[DEBUG] ingestAudio response received: " + (response != null ? response.toString() : "null"));
            Platform.runLater(() -> {
                statusLabel.setText("در حال ضبط...");
                
                if (response != null) {
                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> segments = (List<Map<String, Object>>) response.get("segments");
                    @SuppressWarnings("unchecked")
                    List<String> newSpeakers = (List<String>) response.get("new_speakers");
                    
                    System.out.println("[DEBUG] Segments: " + (segments != null ? segments.size() : 0));
                    System.out.println("[DEBUG] New speakers: " + (newSpeakers != null ? newSpeakers.size() : 0));
                    
                    if (segments != null && !segments.isEmpty()) {
                        for (Map<String, Object> segment : segments) {
                            String speakerId = (String) segment.get("speaker");
                            String text = (String) segment.get("text");
                            
                            if (text != null && !text.isEmpty()) {
                                String displayName = speakerNames.getOrDefault(speakerId, speakerId);
                                System.out.println("[DEBUG] Adding message: " + displayName + ": " + text);
                                chatTimeline.addMessage(displayName, text);
                            }
                        }
                    } else {
                        System.out.println("[DEBUG] No segments in response (might be silence or VAD filtered)");
                    }
                    
                    // Handle new speakers
                    if (newSpeakers != null && !newSpeakers.isEmpty()) {
                        for (String speakerId : newSpeakers) {
                            if (!speakerNames.containsKey(speakerId)) {
                                System.out.println("[DEBUG] New speaker detected: " + speakerId);
                                promptForSpeakerName(speakerId);
                            }
                        }
                    }
                } else {
                    System.out.println("[WARN] ingestAudio returned null response");
                }
            });
        }).exceptionally(e -> {
            System.err.println("[ERROR] Error processing audio chunk: " + e.getMessage());
            e.printStackTrace();
            Platform.runLater(() -> {
                statusLabel.setText("خطا در پردازش صدا");
                statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: red;");
            });
            return null;
        });
    }
    
    private void promptForSpeakerName(String speakerId) {
        speakerPrompt.promptForSpeaker(null, null).thenAccept(optionalName -> {
            Platform.runLater(() -> {
                if (optionalName.isPresent()) {
                    String displayName = optionalName.get();
                    speakerNames.put(speakerId, displayName);
                    
                    // Label speaker in session
                    if (currentSessionId != null) {
                        httpClient.labelSpeaker(currentSessionId, speakerId, displayName);
                    }
                } else {
                    // Use default name
                    speakerNames.put(speakerId, "سخنران " + speakerId.substring(0, 8));
                }
            });
        });
    }
    
    private void exportSummary() {
        if (currentSessionId == null) {
            return;
        }
        
        statusLabel.setText("در حال تولید خلاصه...");
        
        httpClient.exportSession(currentSessionId).thenAccept(export -> {
            Platform.runLater(() -> {
                if (export != null) {
                    saveExport(export);
                    statusLabel.setText("خلاصه ذخیره شد");
                } else {
                    statusLabel.setText("خطا در تولید خلاصه");
                }
            });
        }).exceptionally(e -> {
            Platform.runLater(() -> {
                statusLabel.setText("خطا: " + e.getMessage());
            });
            return null;
        });
    }
    
    @SuppressWarnings("unchecked")
    private void saveExport(Map<String, Object> export) {
        FileChooser fileChooser = new FileChooser();
        fileChooser.setTitle("ذخیره خلاصه جلسه");
        fileChooser.setInitialFileName("meeting-summary-" + currentSessionId + ".md");
        fileChooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("Markdown", "*.md"));
        fileChooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("Text", "*.txt"));
        
        File file = fileChooser.showSaveDialog(null);
        if (file != null) {
            try (FileWriter writer = new FileWriter(file)) {
                // Write metadata
                Map<String, Object> metadata = (Map<String, Object>) export.get("metadata");
                if (metadata != null) {
                    writer.write("# " + metadata.getOrDefault("title", "جلسه") + "\n\n");
                }
                
                // Write summary
                Map<String, Object> summary = (Map<String, Object>) export.get("summary");
                if (summary != null) {
                    writer.write("## خلاصه\n\n");
                    writer.write(summary.getOrDefault("highlight", "") + "\n\n");
                    
                    List<String> bulletPoints = (List<String>) summary.get("bullet_points");
                    if (bulletPoints != null && !bulletPoints.isEmpty()) {
                        writer.write("### نکات کلیدی\n\n");
                        for (String point : bulletPoints) {
                            writer.write("- " + point + "\n");
                        }
                        writer.write("\n");
                    }
                }
                
                // Write segments
                List<Map<String, Object>> segments = (List<Map<String, Object>>) export.get("segments");
                if (segments != null && !segments.isEmpty()) {
                    writer.write("## متن کامل\n\n");
                    for (Map<String, Object> segment : segments) {
                        String speaker = (String) segment.get("speaker");
                        String text = (String) segment.get("text");
                        String displayName = speakerNames.getOrDefault(speaker, speaker);
                        writer.write("**" + displayName + "**: " + text + "\n\n");
                    }
                }
                
                writer.flush();
                statusLabel.setText("فایل ذخیره شد: " + file.getName());
            } catch (IOException e) {
                e.printStackTrace();
                statusLabel.setText("خطا در ذخیره فایل: " + e.getMessage());
            }
        }
    }
    
    public static void main(String[] args) {
        launch(args);
    }
}

