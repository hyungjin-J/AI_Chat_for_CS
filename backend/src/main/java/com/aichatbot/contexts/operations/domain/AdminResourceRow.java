package com.aichatbot.contexts.operations.domain;

import java.time.Instant;
import java.util.UUID;

public record AdminResourceRow(
    UUID id,
    UUID tenantId,
    String resourceType,
    String resourceKey,
    String status,
    String payloadJson,
    Boolean activeFlag,
    Instant lastRotatedAt,
    UUID createdBy,
    UUID updatedBy,
    Instant createdAt,
    Instant updatedAt
) {
}
