package com.aichatbot.global.idempotency;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class IdempotencyService {

    private static final long DEFAULT_TTL_SECONDS = 86400L;

    private final ConcurrentHashMap<String, IdempotencyRecord> records = new ConcurrentHashMap<>();

    public <T> T execute(String scope, String idempotencyKey, Supplier<T> action) {
        pruneExpired();
        String key = scope + ":" + Objects.requireNonNull(idempotencyKey, "idempotencyKey");

        IdempotencyRecord existing = records.get(key);
        if (existing != null) {
            if (existing.inProgress()) {
                throw new ApiException(
                    HttpStatus.CONFLICT,
                    "API-003-409",
                    ErrorCatalog.messageOf("API-003-409"),
                    List.of("duplicate_in_progress")
                );
            }
            @SuppressWarnings("unchecked")
            T cached = (T) existing.response();
            return cached;
        }

        records.put(key, IdempotencyRecord.inProgress(Instant.now().plusSeconds(DEFAULT_TTL_SECONDS)));
        try {
            T response = action.get();
            records.put(key, IdempotencyRecord.completed(response, Instant.now().plusSeconds(DEFAULT_TTL_SECONDS)));
            return response;
        } catch (RuntimeException exception) {
            records.remove(key);
            throw exception;
        }
    }

    private void pruneExpired() {
        Instant now = Instant.now();
        records.entrySet().removeIf(entry -> entry.getValue().expiresAt().isBefore(now));
    }

    private record IdempotencyRecord(boolean inProgress, Object response, Instant expiresAt) {

        static IdempotencyRecord inProgress(Instant expiresAt) {
            return new IdempotencyRecord(true, null, expiresAt);
        }

        static IdempotencyRecord completed(Object response, Instant expiresAt) {
            return new IdempotencyRecord(false, response, expiresAt);
        }
    }
}
