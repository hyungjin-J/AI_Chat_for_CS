package com.aichatbot.contexts.identity.domain;

import java.time.Instant;
import java.util.UUID;

public record MfaChallengeRecord(
    UUID id,
    UUID tenantId,
    UUID userId,
    String challengeType,
    String totpSecretCiphertext,
    Instant expiresAt,
    Instant consumedAt,
    int attemptCount,
    Instant lockedUntil,
    UUID traceId
) {
}


