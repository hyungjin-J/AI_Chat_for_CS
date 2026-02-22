package com.aichatbot.contexts.operations.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class OpsDimensionsSanitizer {

    private static final Set<String> HASH_KEYS = Set.of(
        "tenant_key",
        "tenant_id",
        "user_id",
        "login_id",
        "ip",
        "created_ip",
        "consumed_ip",
        "email",
        "phone"
    );

    private static final Pattern EMAIL_PATTERN = Pattern.compile("[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", Pattern.CASE_INSENSITIVE);
    private static final Pattern PHONE_PATTERN = Pattern.compile("\\+?\\d[\\d\\-\\s]{7,}\\d");
    private static final Pattern IPV4_PATTERN = Pattern.compile("\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b");

    public Map<String, Object> sanitize(Map<String, Object> dimensions) {
        if (dimensions == null || dimensions.isEmpty()) {
            return Map.of();
        }

        Map<String, Object> sanitized = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : dimensions.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            sanitized.put(key, sanitizeValue(key, value));
        }
        return sanitized;
    }

    private Object sanitizeValue(String key, Object value) {
        if (value == null) {
            return null;
        }
        String normalizedKey = key == null ? "" : key.toLowerCase(Locale.ROOT);
        if (HASH_KEYS.contains(normalizedKey)) {
            return "sha256:" + shortHash(String.valueOf(value));
        }
        if (value instanceof String stringValue) {
            String masked = EMAIL_PATTERN.matcher(stringValue).replaceAll("<REDACTED>");
            masked = PHONE_PATTERN.matcher(masked).replaceAll("<REDACTED>");
            masked = IPV4_PATTERN.matcher(masked).replaceAll("<REDACTED>");
            return masked;
        }
        return value;
    }

    private String shortHash(String raw) {
        if (raw == null || raw.isBlank()) {
            return "empty";
        }
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(raw.trim().getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(24);
            for (int index = 0; index < 12 && index < digest.length; index++) {
                builder.append(String.format("%02x", digest[index]));
            }
            return builder.toString();
        } catch (Exception exception) {
            return "hash_error";
        }
    }
}
