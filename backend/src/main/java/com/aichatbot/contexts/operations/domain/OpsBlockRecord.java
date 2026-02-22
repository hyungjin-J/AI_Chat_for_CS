package com.aichatbot.contexts.operations.domain;

import java.time.Instant;
import java.util.UUID;

public record OpsBlockRecord(
    UUID id,
    UUID tenantId,
    String blockType,
    String blockValue,
    String status,
    String reason,
    Instant expiresAt,
    UUID createdBy,
    Instant createdAt,
    Instant updatedAt
) {
}


