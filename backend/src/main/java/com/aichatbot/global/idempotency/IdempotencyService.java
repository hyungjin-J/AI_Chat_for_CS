package com.aichatbot.global.idempotency;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ErrorCatalog;
import java.time.Duration;
import java.util.List;
import java.util.Objects;
import java.util.function.Supplier;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class IdempotencyService {

    private final IdempotencyStore idempotencyStore;
    private final AppProperties appProperties;

    public IdempotencyService(IdempotencyStore idempotencyStore, AppProperties appProperties) {
        this.idempotencyStore = idempotencyStore;
        this.appProperties = appProperties;
    }

    public <T> T execute(String scope, String idempotencyKey, Supplier<T> action) {
        return execute(scope, idempotencyKey, "", action);
    }

    public <T> T execute(String scope, String idempotencyKey, String payloadHash, Supplier<T> action) {
        Duration ttl = Duration.ofSeconds(appProperties.getIdempotency().getTtlSeconds());
        String key = scope + ":" + Objects.requireNonNull(idempotencyKey, "idempotencyKey");

        StoredIdempotencyRecord existing = idempotencyStore.get(key).orElse(null);
        if (existing != null) {
            if (payloadHash != null && !payloadHash.isBlank()
                && existing.payloadHash() != null
                && !existing.payloadHash().isBlank()
                && !payloadHash.equals(existing.payloadHash())) {
                throw duplicateConflict("idempotency_payload_mismatch");
            }
            throw duplicateConflict(existing.inProgress() ? "duplicate_in_progress" : "duplicate_completed");
        }

        boolean reserved = idempotencyStore.putIfAbsent(key, ttl, payloadHash);
        if (!reserved) {
            throw duplicateConflict("duplicate_in_progress");
        }

        try {
            T response = action.get();
            idempotencyStore.markCompleted(key, ttl, "completed", payloadHash);
            return response;
        } catch (RuntimeException exception) {
            idempotencyStore.remove(key);
            throw exception;
        }
    }

    private ApiException duplicateConflict(String detail) {
        return new ApiException(
            HttpStatus.CONFLICT,
            "API-003-409",
            ErrorCatalog.messageOf("API-003-409"),
            List.of(detail)
        );
    }
}
