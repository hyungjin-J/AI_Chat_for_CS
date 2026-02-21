package com.aichatbot.global.audit.domain;

import java.time.Instant;
import java.util.UUID;

public record PersistentAuditLogEntry(
    UUID id,
    UUID tenantId,
    UUID traceId,
    String actionType,
    UUID actorUserId,
    String actorRole,
    String targetType,
    String targetId,
    String beforeJson,
    String afterJson,
    Long chainSeq,
    String hashPrev,
    String hashCurr,
    String hashAlgo,
    Instant createdAt
) {
}
