package com.meetingassistant.app;

import com.meetingassistant.audio.CaptureService;
import com.meetingassistant.transport.GrpcClient;
import com.meetingassistant.ui.ChatTimeline;
import com.meetingassistant.ui.SpeakerPrompt;

/**
 * Minimal entrypoint to prove the desktop scaffold builds.
 * Extend with JavaFX Application subclass and scene wiring per architecture.
 */
public class Main {
    public static void main(String[] args) {
        System.out.println("Meeting Assistant desktop scaffold starting...");
        CaptureService captureService = new CaptureService();
        GrpcClient grpcClient = new GrpcClient();
        ChatTimeline timeline = new ChatTimeline();
        SpeakerPrompt prompt = new SpeakerPrompt();

        // Wire the placeholders together to keep the skeleton compilable.
        captureService.attachVadGate();
        grpcClient.initializeChannel();
        timeline.renderPlaceholder();
        prompt.renderPlaceholder();
    }
}
