package com.aichatbot.global.observability;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

public final class TraceIdNormalizer {

    private TraceIdNormalizer() {
    }

    public static UUID toUuid(String traceId) {
        if (traceId == null || traceId.isBlank()) {
            return UUID.nameUUIDFromBytes("missing-trace".getBytes(StandardCharsets.UTF_8));
        }
        try {
            return UUID.fromString(traceId);
        } catch (IllegalArgumentException exception) {
            return UUID.nameUUIDFromBytes(traceId.getBytes(StandardCharsets.UTF_8));
        }
    }
}
