package com.aichatbot.session.infrastructure;

import java.time.Instant;

public record ConversationRow(
    String id,
    String tenantId,
    String channelId,
    String customerId,
    String status,
    String traceId,
    Instant createdAt
) {
}
