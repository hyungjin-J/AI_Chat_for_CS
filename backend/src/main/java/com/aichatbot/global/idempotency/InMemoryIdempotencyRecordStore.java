package com.aichatbot.global.idempotency;

import java.time.Instant;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

@Component
public class InMemoryIdempotencyRecordStore implements IdempotencyStore {

    private final ConcurrentHashMap<String, StoredIdempotencyRecord> records = new ConcurrentHashMap<>();

    @Override
    public Optional<StoredIdempotencyRecord> get(String key) {
        Instant now = Instant.now();
        StoredIdempotencyRecord record = records.get(key);
        if (record == null) {
            return Optional.empty();
        }
        if (record.isExpired(now)) {
            records.remove(key);
            return Optional.empty();
        }
        return Optional.of(record);
    }

    @Override
    public boolean putIfAbsent(String key, java.time.Duration ttl, String payloadHash) {
        Instant expiresAt = Instant.now().plus(ttl);
        return records.putIfAbsent(key, StoredIdempotencyRecord.inProgress(payloadHash, expiresAt)) == null;
    }

    @Override
    public void markCompleted(String key, java.time.Duration ttl, String resultRef, String payloadHash) {
        Instant expiresAt = Instant.now().plus(ttl);
        records.put(key, StoredIdempotencyRecord.completed(payloadHash, resultRef, null, expiresAt));
    }

    @Override
    public void remove(String key) {
        records.remove(key);
    }
}
