package com.aichatbot.message.application;

import java.time.Instant;
import java.util.UUID;

public record MessageView(
    UUID id,
    UUID tenantId,
    UUID conversationId,
    String role,
    String messageText,
    String traceId,
    Instant createdAt
) {
}
