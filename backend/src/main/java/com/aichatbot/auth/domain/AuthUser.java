package com.aichatbot.auth.domain;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record AuthUser(
    UUID userId,
    UUID tenantId,
    String tenantKey,
    String loginId,
    String displayName,
    List<String> roles,
    long permissionVersion,
    String adminLevel,
    boolean mfaEnabled,
    int failedLoginCount,
    Instant lockedUntil
) {
}
