package com.aichatbot.contexts.billing.infrastructure;

import java.time.Instant;

public record GenerationLogRow(
    String id,
    String tenantId,
    String messageId,
    String providerId,
    String modelId,
    Integer inputTokens,
    Integer outputTokens,
    Integer toolCalls,
    String promptMasked,
    String traceId,
    Instant createdAt
) {
}
