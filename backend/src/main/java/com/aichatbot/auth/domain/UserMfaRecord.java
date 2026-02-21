package com.aichatbot.auth.domain;

import java.time.Instant;
import java.util.UUID;

public record UserMfaRecord(
    UUID id,
    UUID tenantId,
    UUID userId,
    String mfaType,
    String secretCiphertext,
    boolean enabled,
    boolean enforced,
    Instant verifiedAt,
    Instant updatedAt
) {
}
