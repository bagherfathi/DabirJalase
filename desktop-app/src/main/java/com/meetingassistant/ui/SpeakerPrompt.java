package com.meetingassistant.ui;

import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.NodeOrientation;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.GridPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.VBox;
import javafx.stage.Modality;
import javafx.stage.Stage;
import javafx.stage.Window;

import java.util.Optional;
import java.util.concurrent.CompletableFuture;

/**
 * Dialog for prompting user to identify unknown speakers.
 * Shows "Who is this?" dialog when a new speaker is detected.
 */
public class SpeakerPrompt {
    
    /**
     * Show a dialog asking "Who is this?" and return the speaker name.
     * 
     * @param ownerWindow Parent window
     * @param audioPreview Optional audio preview (not implemented yet)
     * @return CompletableFuture that completes with speaker name, or empty if cancelled
     */
    public CompletableFuture<Optional<String>> promptForSpeaker(Window ownerWindow, byte[] audioPreview) {
        CompletableFuture<Optional<String>> future = new CompletableFuture<>();
        
        Platform.runLater(() -> {
            Dialog<String> dialog = new Dialog<>();
            dialog.setTitle("شناسایی سخنران");
            dialog.setHeaderText("این سخنران جدید است. لطفاً نام او را وارد کنید:");
            dialog.initModality(Modality.WINDOW_MODAL);
            dialog.initOwner(ownerWindow);
            
            // RTL support
            dialog.getDialogPane().setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
            
            // Create form
            GridPane grid = new GridPane();
            grid.setHgap(10);
            grid.setVgap(10);
            grid.setPadding(new Insets(20));
            grid.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
            
            Label nameLabel = new Label("نام:");
            nameLabel.setStyle("-fx-font-size: 14px;");
            TextField nameField = new TextField();
            nameField.setPromptText("مثال: احمد رضایی");
            nameField.setPrefWidth(300);
            
            grid.add(nameLabel, 0, 0);
            grid.add(nameField, 1, 0);
            
            // Add audio preview label (placeholder for future implementation)
            Label previewLabel = new Label("پیش‌نمایش صدا: [در حال توسعه]");
            previewLabel.setStyle("-fx-font-size: 12px; -fx-text-fill: gray;");
            grid.add(previewLabel, 0, 1, 2, 1);
            
            dialog.getDialogPane().setContent(grid);
            
            // Buttons
            ButtonType okButtonType = new ButtonType("تأیید", ButtonBar.ButtonData.OK_DONE);
            ButtonType cancelButtonType = new ButtonType("لغو", ButtonBar.ButtonData.CANCEL_CLOSE);
            dialog.getDialogPane().getButtonTypes().addAll(okButtonType, cancelButtonType);
            
            // Enable OK button only when name is entered
            Button okButton = (Button) dialog.getDialogPane().lookupButton(okButtonType);
            okButton.setDisable(true);
            
            nameField.textProperty().addListener((obs, oldVal, newVal) -> {
                okButton.setDisable(newVal.trim().isEmpty());
            });
            
            // Set result converter
            dialog.setResultConverter(dialogButton -> {
                if (dialogButton == okButtonType) {
                    return nameField.getText().trim();
                }
                return null;
            });
            
            // Focus on name field
            Platform.runLater(() -> nameField.requestFocus());
            
            // Show dialog and handle result
            Optional<String> result = dialog.showAndWait();
            future.complete(result);
        });
        
        return future;
    }
    
    /**
     * Show a simple confirmation dialog.
     */
    public boolean confirm(String title, String message, Window ownerWindow) {
        Alert alert = new Alert(Alert.AlertType.CONFIRMATION);
        alert.setTitle(title);
        alert.setHeaderText(message);
        alert.initOwner(ownerWindow);
        alert.getDialogPane().setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT);
        
        Optional<ButtonType> result = alert.showAndWait();
        return result.isPresent() && result.get() == ButtonType.OK;
    }
    
    /**
     * Render placeholder (for compatibility).
     */
    public void renderPlaceholder() {
        System.out.println("[SpeakerPrompt] Ready to show speaker identification dialogs.");
    }
}
