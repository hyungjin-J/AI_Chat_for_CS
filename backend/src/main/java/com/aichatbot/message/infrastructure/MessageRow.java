package com.aichatbot.message.infrastructure;

import java.time.Instant;

public record MessageRow(
    String id,
    String tenantId,
    String conversationId,
    String role,
    String messageText,
    String traceId,
    Instant createdAt
) {
}
