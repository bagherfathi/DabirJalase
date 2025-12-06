package com.meetingassistant.config;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

/**
 * Application configuration manager.
 * Loads configuration from config.properties file with fallback to environment variables and defaults.
 */
public class AppConfig {
    private static AppConfig instance;
    private final Properties properties;
    
    // Default values
    private static final String DEFAULT_SERVER_URL = "http://localhost:8000";
    private static final int DEFAULT_CONNECTION_TIMEOUT = 5000;
    private static final int DEFAULT_READ_TIMEOUT = 10000;
    private static final String DEFAULT_LANGUAGE = "fa";
    private static final int DEFAULT_WINDOW_WIDTH = 900;
    private static final int DEFAULT_WINDOW_HEIGHT = 700;
    
    private AppConfig() {
        properties = new Properties();
        loadConfiguration();
    }
    
    /**
     * Get the singleton instance of AppConfig.
     */
    public static synchronized AppConfig getInstance() {
        if (instance == null) {
            instance = new AppConfig();
        }
        return instance;
    }
    
    /**
     * Load configuration from file, environment variables, or use defaults.
     * Priority: config file > environment variables > defaults
     */
    private void loadConfiguration() {
        // Try to load from config.properties in resources
        try (InputStream resourceStream = getClass().getClassLoader().getResourceAsStream("config.properties")) {
            if (resourceStream != null) {
                properties.load(resourceStream);
                System.out.println("[INFO] Loaded configuration from resources/config.properties");
            }
        } catch (IOException e) {
            System.out.println("[WARN] Could not load config.properties from resources: " + e.getMessage());
        }
        
        // Try to load from config.properties in current directory or user home
        Path[] configPaths = {
            Paths.get("config.properties"),
            Paths.get(System.getProperty("user.home"), ".meetingassistant", "config.properties"),
            Paths.get(System.getProperty("user.dir"), "config.properties")
        };
        
        for (Path configPath : configPaths) {
            if (Files.exists(configPath)) {
                try (InputStream fileStream = Files.newInputStream(configPath)) {
                    properties.load(fileStream);
                    System.out.println("[INFO] Loaded configuration from: " + configPath.toAbsolutePath());
                    break;
                } catch (IOException e) {
                    System.out.println("[WARN] Could not load config from " + configPath + ": " + e.getMessage());
                }
            }
        }
        
        // Override with environment variables if they exist (higher priority)
        String envServerUrl = System.getenv("MEETING_ASSISTANT_SERVER_URL");
        if (envServerUrl != null && !envServerUrl.isEmpty()) {
            properties.setProperty("server.url", envServerUrl);
            System.out.println("[INFO] Overriding server.url with environment variable: " + envServerUrl);
        }
        
        String envApiKey = System.getenv("MEETING_ASSISTANT_API_KEY");
        if (envApiKey != null && !envApiKey.isEmpty()) {
            properties.setProperty("api.key", envApiKey);
        }
        
        // Override with system properties if they exist (highest priority)
        String sysServerUrl = System.getProperty("meeting.assistant.server.url");
        if (sysServerUrl != null && !sysServerUrl.isEmpty()) {
            properties.setProperty("server.url", sysServerUrl);
            System.out.println("[INFO] Overriding server.url with system property: " + sysServerUrl);
        }
    }
    
    /**
     * Get the server URL.
     */
    public String getServerUrl() {
        String url = properties.getProperty("server.url", DEFAULT_SERVER_URL);
        // Ensure URL doesn't end with /
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }
    
    /**
     * Get the API key (may be null/empty if not configured).
     */
    public String getApiKey() {
        String key = properties.getProperty("api.key", "");
        return key.isEmpty() ? null : key;
    }
    
    /**
     * Get the connection timeout in milliseconds.
     */
    public int getConnectionTimeout() {
        return getIntProperty("connection.timeout", DEFAULT_CONNECTION_TIMEOUT);
    }
    
    /**
     * Get the read timeout in milliseconds.
     */
    public int getReadTimeout() {
        return getIntProperty("read.timeout", DEFAULT_READ_TIMEOUT);
    }
    
    /**
     * Get the default language for sessions.
     */
    public String getDefaultLanguage() {
        return properties.getProperty("default.language", DEFAULT_LANGUAGE);
    }
    
    /**
     * Get the window width.
     */
    public int getWindowWidth() {
        return getIntProperty("window.width", DEFAULT_WINDOW_WIDTH);
    }
    
    /**
     * Get the window height.
     */
    public int getWindowHeight() {
        return getIntProperty("window.height", DEFAULT_WINDOW_HEIGHT);
    }
    
    /**
     * Get an integer property with a default value.
     */
    private int getIntProperty(String key, int defaultValue) {
        String value = properties.getProperty(key);
        if (value == null || value.isEmpty()) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            System.out.println("[WARN] Invalid integer value for " + key + ": " + value + ", using default: " + defaultValue);
            return defaultValue;
        }
    }
    
    /**
     * Get a property value.
     */
    public String getProperty(String key, String defaultValue) {
        return properties.getProperty(key, defaultValue);
    }
    
    /**
     * Set a property value (runtime override).
     */
    public void setProperty(String key, String value) {
        properties.setProperty(key, value);
    }
    
    /**
     * Print current configuration (for debugging).
     */
    public void printConfiguration() {
        System.out.println("[INFO] Current configuration:");
        System.out.println("  server.url: " + getServerUrl());
        System.out.println("  api.key: " + (getApiKey() != null ? "***" : "not set"));
        System.out.println("  connection.timeout: " + getConnectionTimeout());
        System.out.println("  read.timeout: " + getReadTimeout());
        System.out.println("  default.language: " + getDefaultLanguage());
        System.out.println("  window.width: " + getWindowWidth());
        System.out.println("  window.height: " + getWindowHeight());
    }
}

