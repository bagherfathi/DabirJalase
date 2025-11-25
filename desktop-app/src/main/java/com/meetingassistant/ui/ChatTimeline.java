package com.meetingassistant.ui;

import javafx.application.Platform;
import javafx.geometry.NodeOrientation;
import javafx.geometry.Pos;
import javafx.scene.control.Label;
import javafx.scene.control.ScrollPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.VBox;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;
import javafx.scene.text.TextAlignment;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * RTL-friendly chat timeline for displaying meeting transcripts.
 * Shows speaker quotes in a chat-style interface with proper Farsi RTL support.
 */
public class ChatTimeline {
    private final VBox messageContainer;
    private final ScrollPane scrollPane;
    private final Map<String, Color> speakerColors = new HashMap<>();
    private final List<Color> colorPalette = List.of(
        Color.web("#4A90E2"), Color.web("#50C878"), Color.web("#FF6B6B"),
        Color.web("#FFA500"), Color.web("#9B59B6"), Color.web("#1ABC9C"),
        Color.web("#E74C3C"), Color.web("#3498DB")
    );
    private int colorIndex = 0;
    
    public ChatTimeline() {
        messageContainer = new VBox(10);
        messageContainer.setStyle("-fx-padding: 15px; -fx-background-color: #f5f5f5;");
        messageContainer.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT); // RTL for Farsi
        
        scrollPane = new ScrollPane(messageContainer);
        scrollPane.setFitToWidth(true);
        scrollPane.setStyle("-fx-background: #f5f5f5;");
        scrollPane.setVvalue(1.0); // Scroll to bottom
        
        // Auto-scroll to bottom when new messages are added
        messageContainer.heightProperty().addListener((obs, oldVal, newVal) -> {
            Platform.runLater(() -> scrollPane.setVvalue(1.0));
        });
    }
    
    public ScrollPane getView() {
        return scrollPane;
    }
    
    /**
     * Add a message to the timeline.
     */
    public void addMessage(String speakerName, String text, LocalDateTime timestamp) {
        Platform.runLater(() -> {
            HBox messageBox = createMessageBox(speakerName, text, timestamp);
            messageContainer.getChildren().add(messageBox);
        });
    }
    
    /**
     * Add a message with current timestamp.
     */
    public void addMessage(String speakerName, String text) {
        addMessage(speakerName, text, LocalDateTime.now());
    }
    
    private HBox createMessageBox(String speakerName, String text, LocalDateTime timestamp) {
        HBox messageBox = new HBox(10);
        messageBox.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
        messageBox.setAlignment(Pos.TOP_RIGHT);
        messageBox.setStyle("-fx-padding: 8px;");
        
        // Speaker name label
        Label speakerLabel = new Label(speakerName + ":");
        speakerLabel.setFont(Font.font("Tahoma", 14));
        speakerLabel.setTextFill(getSpeakerColor(speakerName));
        speakerLabel.setStyle("-fx-font-weight: bold; -fx-padding: 0 8px 0 0;");
        
        // Message text label
        Label textLabel = new Label(text);
        textLabel.setFont(Font.font("Tahoma", 13));
        textLabel.setWrapText(true);
        textLabel.setMaxWidth(600);
        textLabel.setTextAlignment(TextAlignment.RIGHT);
        textLabel.setStyle("-fx-background-color: white; -fx-background-radius: 8px; " +
                          "-fx-padding: 10px; -fx-border-radius: 8px; " +
                          "-fx-effect: dropshadow(three-pass-box, rgba(0,0,0,0.1), 5, 0, 0, 2);");
        
        // Timestamp label
        String timeStr = timestamp.format(DateTimeFormatter.ofPattern("HH:mm"));
        Label timeLabel = new Label(timeStr);
        timeLabel.setFont(Font.font("Tahoma", 10));
        timeLabel.setTextFill(Color.GRAY);
        timeLabel.setStyle("-fx-padding: 4px 0 0 0;");
        
        VBox contentBox = new VBox(4);
        contentBox.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
        contentBox.getChildren().addAll(textLabel, timeLabel);
        
        messageBox.getChildren().addAll(contentBox, speakerLabel);
        
        return messageBox;
    }
    
    private Color getSpeakerColor(String speakerName) {
        if (!speakerColors.containsKey(speakerName)) {
            Color color = colorPalette.get(colorIndex % colorPalette.size());
            speakerColors.put(speakerName, color);
            colorIndex++;
        }
        return speakerColors.get(speakerName);
    }
    
    /**
     * Clear all messages.
     */
    public void clear() {
        Platform.runLater(() -> {
            messageContainer.getChildren().clear();
            speakerColors.clear();
            colorIndex = 0;
        });
    }
    
    /**
     * Highlight a specific speaker's messages.
     */
    public void highlightSpeaker(String speakerName, boolean highlight) {
        Platform.runLater(() -> {
            for (var node : messageContainer.getChildren()) {
                if (node instanceof HBox) {
                    HBox messageBox = (HBox) node;
                    // Check if this message belongs to the speaker
                    // (simplified - in real implementation, store speaker info with message)
                    if (highlight) {
                        messageBox.setStyle("-fx-padding: 8px; -fx-background-color: #fff9c4; -fx-background-radius: 4px;");
                    } else {
                        messageBox.setStyle("-fx-padding: 8px;");
                    }
                }
            }
        });
    }
}
