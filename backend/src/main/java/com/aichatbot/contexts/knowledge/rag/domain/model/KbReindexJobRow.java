package com.aichatbot.contexts.knowledge.rag.domain.model;

import java.time.Instant;
import java.util.UUID;

public record KbReindexJobRow(
    UUID id,
    UUID tenantId,
    String jobType,
    UUID documentVersionId,
    String idempotencyKey,
    String status,
    Integer attemptCount,
    Integer maxAttempts,
    Instant nextRetryAt,
    String errorCode,
    String errorExcerpt,
    UUID requestedBy,
    Instant requestedAt,
    Instant startedAt,
    Instant completedAt,
    String resultMessage,
    UUID lastTraceId
) {
}
