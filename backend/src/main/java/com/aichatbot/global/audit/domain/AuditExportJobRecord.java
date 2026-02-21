package com.aichatbot.global.audit.domain;

import java.time.Instant;
import java.util.UUID;

public record AuditExportJobRecord(
    UUID id,
    UUID tenantId,
    UUID requestedBy,
    String status,
    String exportFormat,
    Instant fromUtc,
    Instant toUtc,
    Integer rowLimit,
    Integer maxBytes,
    Integer maxDurationSec,
    Integer rowCount,
    Integer totalBytes,
    String errorCode,
    String errorMessage,
    Instant expiresAt,
    Instant createdAt,
    Instant startedAt,
    Instant completedAt,
    UUID traceId
) {
}
