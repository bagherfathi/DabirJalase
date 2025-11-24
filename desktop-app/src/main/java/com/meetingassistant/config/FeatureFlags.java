package com.meetingassistant.config;

import java.util.Collections;
import java.util.Map;

/**
 * Lightweight feature flag placeholder.
 */
public class FeatureFlags {
    private final Map<String, Boolean> flags;

    public FeatureFlags(Map<String, Boolean> flags) {
        this.flags = flags;
    }

    public boolean isEnabled(String flag) {
        return flags.getOrDefault(flag, false);
    }

    public static FeatureFlags empty() {
        return new FeatureFlags(Collections.emptyMap());
    }
}
