package com.aichatbot.global.idempotency;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.message.application.MvpObservabilityMetrics;
import java.time.Duration;
import java.util.Locale;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
@Primary
public class IdempotencyStoreRouter implements IdempotencyStore {

    private static final Logger log = LoggerFactory.getLogger(IdempotencyStoreRouter.class);

    private final InMemoryIdempotencyRecordStore inMemoryStore;
    private final RedisIdempotencyStore redisStore;
    private final AppProperties appProperties;
    private final MvpObservabilityMetrics mvpObservabilityMetrics;

    public IdempotencyStoreRouter(
        InMemoryIdempotencyRecordStore inMemoryStore,
        ObjectProvider<RedisIdempotencyStore> redisStoreProvider,
        AppProperties appProperties,
        MvpObservabilityMetrics mvpObservabilityMetrics
    ) {
        this.inMemoryStore = inMemoryStore;
        this.redisStore = redisStoreProvider.getIfAvailable();
        this.appProperties = appProperties;
        this.mvpObservabilityMetrics = mvpObservabilityMetrics;
    }

    @Override
    public boolean putIfAbsent(String key, Duration ttl, String payloadHash) {
        IdempotencyStore delegate = selectPrimaryStore();
        try {
            return delegate.putIfAbsent(toKey(key), ttl, payloadHash);
        } catch (RuntimeException exception) {
            return handleRedisFailure("putIfAbsent", key, () -> inMemoryStore.putIfAbsent(key, ttl, payloadHash), exception);
        }
    }

    @Override
    public Optional<StoredIdempotencyRecord> get(String key) {
        IdempotencyStore delegate = selectPrimaryStore();
        try {
            return delegate.get(toKey(key));
        } catch (RuntimeException exception) {
            return handleRedisFailure("get", key, () -> inMemoryStore.get(key), exception);
        }
    }

    @Override
    public void markCompleted(String key, Duration ttl, String resultRef, String payloadHash) {
        IdempotencyStore delegate = selectPrimaryStore();
        try {
            delegate.markCompleted(toKey(key), ttl, resultRef, payloadHash);
        } catch (RuntimeException exception) {
            handleRedisFailure("markCompleted", key, () -> {
                inMemoryStore.markCompleted(key, ttl, resultRef, payloadHash);
                return null;
            }, exception);
        }
    }

    @Override
    public void remove(String key) {
        IdempotencyStore delegate = selectPrimaryStore();
        try {
            delegate.remove(toKey(key));
        } catch (RuntimeException exception) {
            handleRedisFailure("remove", key, () -> {
                inMemoryStore.remove(key);
                return null;
            }, exception);
        }
    }

    private IdempotencyStore selectPrimaryStore() {
        String mode = appProperties.getIdempotency().getStore().toLowerCase(Locale.ROOT);
        if ("redis".equals(mode) && redisStore != null) {
            return redisStore;
        }
        return inMemoryStore;
    }

    private String toKey(String key) {
        if (selectPrimaryStore() == redisStore) {
            return appProperties.getIdempotency().getRedisKeyPrefix() + key;
        }
        return key;
    }

    private <T> T handleRedisFailure(String operation, String key, FallbackOperation<T> fallback, RuntimeException exception) {
        mvpObservabilityMetrics.recordIdempotencyRedisFallback();
        String strategy = appProperties.getIdempotency().getRedisFailStrategy().toLowerCase(Locale.ROOT);
        if ("fail_closed".equals(strategy)) {
            log.error(
                "idempotency redis unavailable; fail-closed strategy applied. operation={} key={} cause={}",
                operation,
                key,
                exception.getMessage()
            );
            throw new ApiException(
                HttpStatus.SERVICE_UNAVAILABLE,
                "SYS-003-503",
                ErrorCatalog.messageOf("SYS-003-503"),
                java.util.List.of("idempotency_store_unavailable")
            );
        }

        log.warn(
            "idempotency redis unavailable; fallback-memory strategy applied. operation={} key={} cause={}",
            operation,
            key,
            exception.getMessage()
        );
        return fallback.run();
    }

    @FunctionalInterface
    private interface FallbackOperation<T> {
        T run();
    }
}
