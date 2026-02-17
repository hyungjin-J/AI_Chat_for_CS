package com.aichatbot.billing.domain.model;

import java.time.Instant;

public record GenerationLogEntry(
    String id,
    String tenantId,
    String messageId,
    String providerId,
    String modelId,
    int inputTokens,
    int outputTokens,
    int toolCalls,
    String promptMasked,
    String traceId,
    Instant createdAt
) {
}

