package com.aichatbot.contexts.identity.domain;

import java.time.Instant;
import java.util.UUID;

public record AuthSessionOverview(
    UUID sessionId,
    Instant createdAt,
    Instant lastSeenAt,
    Instant expiresAt,
    String clientType,
    String deviceName,
    String createdIp,
    String consumedIp
) {
}


