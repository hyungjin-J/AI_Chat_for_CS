package com.aichatbot.auth.domain;

import java.time.Instant;
import java.util.UUID;

public record AuthSessionRecord(
    UUID id,
    UUID tenantId,
    UUID userId,
    UUID sessionFamilyId,
    String sessionTokenHash,
    String refreshJtiHash,
    String parentRefreshJtiHash,
    Instant expiresAt,
    Instant consumedAt,
    Instant revokedAt
) {
}

