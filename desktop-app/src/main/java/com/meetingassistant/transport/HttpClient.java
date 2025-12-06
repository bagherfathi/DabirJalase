package com.meetingassistant.transport;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/**
 * HTTP client for communicating with Python services.
 * Handles audio ingestion, transcription, diarization, and export.
 */
public class HttpClient {
    private final String baseUrl;
    private final String apiKey;
    private final Gson gson = new Gson();
    
    public HttpClient(String baseUrl) {
        this(baseUrl, null);
    }
    
    public HttpClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey;
    }
    
    /**
     * Check service health.
     */
    public CompletableFuture<Map<String, Object>> health() {
        return CompletableFuture.supplyAsync(() -> {
            return get("/health");
        });
    }
    
    /**
     * Create a new session.
     */
    public CompletableFuture<Map<String, Object>> createSession(String sessionId, String language, String title) {
        System.out.println("[DEBUG] HttpClient.createSession() called: sessionId=" + sessionId + ", language=" + language);
        return CompletableFuture.supplyAsync(() -> {
            Map<String, Object> payload = new HashMap<>();
            payload.put("session_id", sessionId);
            payload.put("language", language);
            if (title != null) {
                payload.put("title", title);
            }
            System.out.println("[DEBUG] Sending POST to /sessions with payload: " + payload);
            Map<String, Object> result = post("/sessions", payload);
            System.out.println("[DEBUG] POST /sessions response: " + result);
            return result;
        });
    }
    
    /**
     * Ingest audio chunk with VAD detection.
     */
    public CompletableFuture<Map<String, Object>> ingestAudio(String sessionId, byte[] audioData, int sampleRate) {
        System.out.println("[DEBUG] HttpClient.ingestAudio() called: sessionId=" + sessionId + ", audioData.length=" + audioData.length + ", sampleRate=" + sampleRate);
        return CompletableFuture.supplyAsync(() -> {
            // Convert audio bytes to float samples
            List<Float> samples = new ArrayList<>();
            for (int i = 0; i < audioData.length - 1; i += 2) {
                int sample = (audioData[i] & 0xFF) | ((audioData[i + 1] & 0xFF) << 8);
                if (sample > 32767) {
                    sample -= 65536;
                }
                samples.add(sample / 32768.0f);
            }
            
            System.out.println("[DEBUG] Converted " + audioData.length + " bytes to " + samples.size() + " float samples");
            
            Map<String, Object> payload = new HashMap<>();
            payload.put("samples", samples);
            payload.put("threshold", 0.01);
            payload.put("min_run", 3);
            payload.put("transcript_hint", "speech detected");
            
            System.out.println("[DEBUG] Sending POST to /sessions/" + sessionId + "/ingest");
            Map<String, Object> result = post("/sessions/" + sessionId + "/ingest", payload);
            System.out.println("[DEBUG] POST /sessions/" + sessionId + "/ingest response: " + (result != null ? "success" : "null"));
            return result;
        });
    }
    
    /**
     * Get session summary.
     */
    public CompletableFuture<Map<String, Object>> getSummary(String sessionId) {
        return CompletableFuture.supplyAsync(() -> {
            return get("/sessions/" + sessionId + "/summary");
        });
    }
    
    /**
     * Export session.
     */
    public CompletableFuture<Map<String, Object>> exportSession(String sessionId) {
        return CompletableFuture.supplyAsync(() -> {
            return get("/sessions/" + sessionId + "/export");
        });
    }
    
    /**
     * Label a speaker.
     */
    public CompletableFuture<Map<String, Object>> labelSpeaker(String sessionId, String speakerId, String displayName) {
        return CompletableFuture.supplyAsync(() -> {
            Map<String, Object> payload = new HashMap<>();
            payload.put("speaker_id", speakerId);
            payload.put("display_name", displayName);
            return post("/sessions/" + sessionId + "/speakers", payload);
        });
    }
    
    /**
     * Get session data.
     */
    public CompletableFuture<Map<String, Object>> getSession(String sessionId) {
        return CompletableFuture.supplyAsync(() -> {
            return get("/sessions/" + sessionId);
        });
    }
    
    // Private helper methods
    
    private Map<String, Object> get(String path) {
        try {
            String fullUrl = baseUrl + path;
            System.out.println("[DEBUG] Making GET request to: " + fullUrl);
            URL url = new URL(fullUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Accept", "application/json");
            // Timeouts will be set by caller if needed, using defaults here
            conn.setConnectTimeout(5000); // 5 second connection timeout
            conn.setReadTimeout(10000); // 10 second read timeout
            if (apiKey != null) {
                conn.setRequestProperty("x-api-key", apiKey);
            }
            
            int responseCode = conn.getResponseCode();
            System.out.println("[DEBUG] Response code: " + responseCode);
            String response = readResponse(conn);
            System.out.println("[DEBUG] Response body: " + response);
            
            if (responseCode >= 200 && responseCode < 300) {
                if (response == null || response.trim().isEmpty()) {
                    System.out.println("[WARN] Empty response body");
                    return new HashMap<>();
                }
                return parseJson(response);
            } else {
                throw new RuntimeException("HTTP " + responseCode + ": " + response);
            }
        } catch (java.net.ConnectException e) {
            System.err.println("[ERROR] Connection refused to " + baseUrl + path);
            throw new RuntimeException("Connection refused: " + e.getMessage(), e);
        } catch (java.net.SocketTimeoutException e) {
            System.err.println("[ERROR] Connection timeout to " + baseUrl + path);
            throw new RuntimeException("Connection timeout: " + e.getMessage(), e);
        } catch (java.net.UnknownHostException e) {
            System.err.println("[ERROR] Unknown host: " + baseUrl);
            throw new RuntimeException("Unknown host: " + e.getMessage(), e);
        } catch (IOException e) {
            System.err.println("[ERROR] IO error making GET request to " + path + ": " + e.getMessage());
            throw new RuntimeException("Error making GET request to " + path + ": " + e.getMessage(), e);
        }
    }
    
    private Map<String, Object> post(String path, Map<String, Object> payload) {
        try {
            URL url = new URL(baseUrl + path);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Accept", "application/json");
            if (apiKey != null) {
                conn.setRequestProperty("x-api-key", apiKey);
            }
            conn.setDoOutput(true);
            
            String jsonPayload = gson.toJson(payload);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(jsonPayload.getBytes(StandardCharsets.UTF_8));
            }
            
            int responseCode = conn.getResponseCode();
            String response = readResponse(conn);
            
            if (responseCode >= 200 && responseCode < 300) {
                return parseJson(response);
            } else {
                throw new RuntimeException("HTTP " + responseCode + ": " + response);
            }
        } catch (IOException e) {
            throw new RuntimeException("Error making POST request to " + path, e);
        }
    }
    
    private String readResponse(HttpURLConnection conn) throws IOException {
        InputStream inputStream = conn.getResponseCode() >= 400 ? conn.getErrorStream() : conn.getInputStream();
        if (inputStream == null) {
            return "";
        }
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
            return response.toString();
        }
    }
    
    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        JsonObject jsonObject = JsonParser.parseString(json).getAsJsonObject();
        return gson.fromJson(jsonObject, Map.class);
    }
}

