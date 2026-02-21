package com.aichatbot.auth.domain;

import java.time.Instant;
import java.util.UUID;

public record AuthUserProjection(
    UUID userId,
    UUID tenantId,
    String tenantKey,
    String loginId,
    String displayName,
    Long permissionVersion,
    String adminLevel,
    Boolean mfaEnabled,
    Integer failedLoginCount,
    Instant lockedUntil
) {
}
