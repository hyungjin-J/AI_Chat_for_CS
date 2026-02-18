package com.aichatbot.message.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.error.QuotaExceededException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class SseConcurrencyGuard {

    private final AppProperties appProperties;
    private final ConcurrentHashMap<String, AtomicInteger> activeConnections = new ConcurrentHashMap<>();

    public SseConcurrencyGuard(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    public void acquire(String userKey) {
        AtomicInteger counter = activeConnections.computeIfAbsent(userKey, ignored -> new AtomicInteger(0));
        int current = counter.incrementAndGet();
        int limit = appProperties.getBudget().getSseConcurrencyMaxPerUser();
        if (current > limit) {
            counter.decrementAndGet();
            throw new QuotaExceededException(
                HttpStatus.TOO_MANY_REQUESTS,
                "API-008-429-SSE",
                ErrorCatalog.messageOf("API-008-429-SSE"),
                limit,
                Math.max(0, limit - (current - 1)),
                Instant.now().plus(10, ChronoUnit.SECONDS).getEpochSecond(),
                10L
            );
        }
    }

    public void release(String userKey) {
        AtomicInteger counter = activeConnections.get(userKey);
        if (counter == null) {
            return;
        }
        int remaining = counter.decrementAndGet();
        if (remaining <= 0) {
            activeConnections.remove(userKey);
        }
    }
}
