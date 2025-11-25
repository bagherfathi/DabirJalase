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
    private Label statusLabel;
    
    @Override
    public void start(Stage primaryStage) {
        // Initialize components
        captureService = new CaptureService();
        httpClient = new HttpClient("http://localhost:8000");
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
        
        statusLabel = new Label("آماده");
        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px;");
        
        controlsBox.getChildren().addAll(startStopButton, exportButton, statusLabel);
        root.setTop(controlsBox);
        
        // Center: Chat timeline
        ScrollPane timelineScroll = chatTimeline.getView();
        root.setCenter(timelineScroll);
        
        // Setup audio capture listener
        captureService.addChunkListener((audioData, sampleRate) -> {
            if (currentSessionId != null && isRecording) {
                handleAudioChunk(audioData, sampleRate);
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
        try {
            // Create new session
            currentSessionId = UUID.randomUUID().toString();
            String title = "جلسه " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
            
            httpClient.createSession(currentSessionId, "fa", title).thenAccept(session -> {
                Platform.runLater(() -> {
                    isRecording = true;
                    startStopButton.setText("توقف ضبط");
                    exportButton.setDisable(false);
                    statusLabel.setText("در حال ضبط...");
                    statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px; -fx-text-fill: green;");
                    chatTimeline.clear();
                    speakerNames.clear();
                });
                
                // Start audio capture
                Platform.runLater(() -> {
                    try {
                        captureService.startCapture();
                    } catch (Exception e) {
                        e.printStackTrace();
                        Platform.runLater(() -> {
                            statusLabel.setText("خطا در شروع ضبط: " + e.getMessage());
                            isRecording = false;
                            startStopButton.setText("شروع ضبط");
                        });
                    }
                });
            }).exceptionally(e -> {
                Platform.runLater(() -> {
                    statusLabel.setText("خطا در ایجاد session: " + e.getMessage());
                });
                return null;
            });
        } catch (Exception e) {
            e.printStackTrace();
            statusLabel.setText("خطا: " + e.getMessage());
        }
    }
    
    private void stopRecording() {
        isRecording = false;
        captureService.stopCapture();
        startStopButton.setText("شروع ضبط");
        statusLabel.setText("ضبط متوقف شد");
        statusLabel.setStyle("-fx-font-size: 12px; -fx-padding: 8px;");
    }
    
    private void handleAudioChunk(byte[] audioData, int sampleRate) {
        if (currentSessionId == null) {
            return;
        }
        
        httpClient.ingestAudio(currentSessionId, audioData, sampleRate).thenAccept(response -> {
            Platform.runLater(() -> {
                if (response != null) {
                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> segments = (List<Map<String, Object>>) response.get("segments");
                    @SuppressWarnings("unchecked")
                    List<String> newSpeakers = (List<String>) response.get("new_speakers");
                    
                    if (segments != null) {
                        for (Map<String, Object> segment : segments) {
                            String speakerId = (String) segment.get("speaker");
                            String text = (String) segment.get("text");
                            
                            if (text != null && !text.isEmpty()) {
                                String displayName = speakerNames.getOrDefault(speakerId, speakerId);
                                chatTimeline.addMessage(displayName, text);
                            }
                        }
                    }
                    
                    // Handle new speakers
                    if (newSpeakers != null && !newSpeakers.isEmpty()) {
                        for (String speakerId : newSpeakers) {
                            if (!speakerNames.containsKey(speakerId)) {
                                promptForSpeakerName(speakerId);
                            }
                        }
                    }
                }
            });
        }).exceptionally(e -> {
            System.err.println("Error processing audio chunk: " + e.getMessage());
            e.printStackTrace();
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

