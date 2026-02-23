package com.aichatbot.contexts.identity.rbac.domain.model;

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

