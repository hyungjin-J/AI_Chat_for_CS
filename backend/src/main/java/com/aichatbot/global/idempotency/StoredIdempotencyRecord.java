package com.aichatbot.global.idempotency;

import java.time.Instant;

public record StoredIdempotencyRecord(
    String payloadHash,
    boolean inProgress,
    String resultRef,
    Object response,
    Instant expiresAt
) {

    public boolean isExpired(Instant now) {
        return expiresAt != null && expiresAt.isBefore(now);
    }

    public static StoredIdempotencyRecord inProgress(String payloadHash, Instant expiresAt) {
        return new StoredIdempotencyRecord(payloadHash, true, null, null, expiresAt);
    }

    public static StoredIdempotencyRecord completed(
        String payloadHash,
        String resultRef,
        Object response,
        Instant expiresAt
    ) {
        return new StoredIdempotencyRecord(payloadHash, false, resultRef, response, expiresAt);
    }
}
