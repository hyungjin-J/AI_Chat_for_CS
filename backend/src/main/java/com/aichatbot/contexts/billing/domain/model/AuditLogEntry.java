package com.aichatbot.contexts.billing.domain.model;

import java.time.Instant;

public record AuditLogEntry(
    String id,
    String tenantId,
    String actorUserId,
    String actorRole,
    String actionType,
    String targetType,
    String targetId,
    String traceId,
    String beforeJson,
    String afterJson,
    Instant createdAt
) {
}


