package com.aichatbot.global.idempotency;

import java.time.Duration;
import java.util.Optional;

public interface IdempotencyStore {

    boolean putIfAbsent(String key, Duration ttl, String payloadHash);

    Optional<StoredIdempotencyRecord> get(String key);

    void markCompleted(String key, Duration ttl, String resultRef, String payloadHash);

    void remove(String key);
}

