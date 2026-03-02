package com.aichatbot.contexts.operations.domain;

import java.time.Instant;
import java.util.UUID;

public record OpsRollbackRow(
    UUID id,
    UUID tenantId,
    String targetType,
    String targetId,
    String status,
    String reason,
    UUID requestedBy,
    Instant createdAt
) {
}
