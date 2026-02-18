package com.aichatbot.global.idempotency;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
public class RedisIdempotencyStore implements IdempotencyStore {

    private static final String STATUS_IN_PROGRESS = "in_progress";
    private static final String STATUS_COMPLETED = "completed";

    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    public RedisIdempotencyStore(StringRedisTemplate stringRedisTemplate, ObjectMapper objectMapper) {
        this.stringRedisTemplate = stringRedisTemplate;
        this.objectMapper = objectMapper;
    }

    @Override
    public boolean putIfAbsent(String key, Duration ttl, String payloadHash) {
        String value = toJson(Map.of(
            "status", STATUS_IN_PROGRESS,
            "payload_hash", payloadHash == null ? "" : payloadHash,
            "created_at", Instant.now().toString()
        ));
        Boolean stored = stringRedisTemplate.opsForValue().setIfAbsent(key, value, ttl);
        return Boolean.TRUE.equals(stored);
    }

    @Override
    public Optional<StoredIdempotencyRecord> get(String key) {
        String value = stringRedisTemplate.opsForValue().get(key);
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }
        try {
            Map<?, ?> map = objectMapper.readValue(value, Map.class);
            Object statusObj = map.get("status");
            Object payloadHashObj = map.get("payload_hash");
            Object resultRefObj = map.get("result_ref");
            String status = statusObj == null ? STATUS_IN_PROGRESS : String.valueOf(statusObj);
            String payloadHash = payloadHashObj == null ? "" : String.valueOf(payloadHashObj);
            String resultRef = resultRefObj == null ? null : String.valueOf(resultRefObj);
            boolean inProgress = STATUS_IN_PROGRESS.equals(status);
            return Optional.of(new StoredIdempotencyRecord(
                payloadHash,
                inProgress,
                resultRef,
                null,
                null
            ));
        } catch (Exception exception) {
            throw new IllegalStateException("idempotency_redis_value_parse_failed", exception);
        }
    }

    @Override
    public void markCompleted(String key, Duration ttl, String resultRef, String payloadHash) {
        String value = toJson(Map.of(
            "status", STATUS_COMPLETED,
            "payload_hash", payloadHash == null ? "" : payloadHash,
            "result_ref", resultRef == null ? "" : resultRef,
            "completed_at", Instant.now().toString()
        ));
        stringRedisTemplate.opsForValue().set(key, value, ttl);
    }

    @Override
    public void remove(String key) {
        stringRedisTemplate.delete(key);
    }

    private String toJson(Map<String, Object> data) {
        try {
            return objectMapper.writeValueAsString(data);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("idempotency_redis_value_serialize_failed", exception);
        }
    }
}
