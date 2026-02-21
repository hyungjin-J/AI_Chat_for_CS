package com.aichatbot.admin.infrastructure;

import java.time.Instant;
import java.util.UUID;

public record RbacChangeRequestRecord(
    UUID id,
    UUID tenantId,
    String resourceKey,
    String roleCode,
    String adminLevel,
    Boolean allowed,
    String status,
    UUID requestedBy,
    String reason,
    Instant appliedAt,
    Instant createdAt,
    Instant updatedAt
) {
}
