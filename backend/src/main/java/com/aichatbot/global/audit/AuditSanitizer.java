package com.aichatbot.global.audit;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class AuditSanitizer {

    private static final String MASK = "***REDACTED***";
    private static final Set<String> SENSITIVE_KEYS = Set.of(
        "password",
        "token",
        "access_token",
        "refresh_token",
        "refresh_jti",
        "secret",
        "api_key",
        "authorization"
    );

    private final ObjectMapper objectMapper;

    public AuditSanitizer(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public String sanitize(Object rawValue) {
        if (rawValue == null) {
            return "{}";
        }

        JsonNode inputNode = objectMapper.valueToTree(rawValue);
        JsonNode sanitized = sanitizeNode(inputNode, null);

        try {
            return objectMapper.writeValueAsString(sanitized);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Failed to serialize sanitized audit payload", exception);
        }
    }

    private JsonNode sanitizeNode(JsonNode node, String fieldName) {
        if (fieldName != null && isSensitiveField(fieldName)) {
            return objectMapper.getNodeFactory().textNode(MASK);
        }

        if (node == null || node.isNull()) {
            return objectMapper.nullNode();
        }

        if (node.isObject()) {
            ObjectNode objectNode = objectMapper.createObjectNode();
            node.fields().forEachRemaining(entry ->
                objectNode.set(entry.getKey(), sanitizeNode(entry.getValue(), entry.getKey()))
            );
            return objectNode;
        }

        if (node.isArray()) {
            ArrayNode arrayNode = objectMapper.createArrayNode();
            for (JsonNode item : node) {
                arrayNode.add(sanitizeNode(item, fieldName));
            }
            return arrayNode;
        }

        if (node.isTextual() && maybeSensitiveText(node.asText())) {
            return objectMapper.getNodeFactory().textNode(MASK);
        }

        return node;
    }

    private boolean isSensitiveField(String fieldName) {
        String normalized = fieldName.toLowerCase(Locale.ROOT);
        if (SENSITIVE_KEYS.contains(normalized)) {
            return true;
        }
        return normalized.endsWith("_token")
            || normalized.endsWith("token")
            || normalized.endsWith("_secret")
            || normalized.endsWith("_api_key")
            || normalized.endsWith("_password");
    }

    private boolean maybeSensitiveText(String value) {
        if (value == null || value.isBlank()) {
            return false;
        }
        // Why: Raw bearer/JWT-like strings should never land in audit before/after payloads.
        if (value.startsWith("eyJ") && value.contains(".")) {
            return true;
        }
        return value.length() > 48 && value.chars().filter(ch -> ch == '.').count() >= 2;
    }
}

