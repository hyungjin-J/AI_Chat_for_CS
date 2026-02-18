package com.aichatbot.session.application;

import java.time.Instant;
import java.util.UUID;

public record ConversationView(
    UUID id,
    UUID tenantId,
    UUID channelId,
    UUID customerId,
    String status,
    String traceId,
    Instant createdAt
) {
}
