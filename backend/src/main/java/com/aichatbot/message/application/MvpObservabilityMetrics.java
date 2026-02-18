package com.aichatbot.message.application;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

@Component
public class MvpObservabilityMetrics {

    private final AtomicLong totalResponses = new AtomicLong();
    private final AtomicLong failClosedResponses = new AtomicLong();
    private final AtomicLong totalAnswerResponses = new AtomicLong();
    private final AtomicLong answerResponsesWithCitation = new AtomicLong();
    private final AtomicLong idempotencyRedisFallbackTotal = new AtomicLong();
    private final Timer sseFirstTokenSeconds;

    public MvpObservabilityMetrics(MeterRegistry meterRegistry) {
        this.sseFirstTokenSeconds = Timer.builder("sse_first_token_seconds")
            .description("Elapsed time in seconds from SSE open to first token event")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(meterRegistry);

        Gauge.builder("fail_closed_rate", this, MvpObservabilityMetrics::failClosedRate)
            .description("Ratio of fail-closed responses to total responses")
            .register(meterRegistry);

        Gauge.builder("citation_coverage", this, MvpObservabilityMetrics::citationCoverage)
            .description("Ratio of answer responses that include at least one citation")
            .register(meterRegistry);

        Gauge.builder("idempotency_redis_fallback_total", this, MvpObservabilityMetrics::idempotencyRedisFallbackTotal)
            .description("Count of times idempotency store fallback was triggered")
            .register(meterRegistry);
    }

    public void recordGenerationOutcome(boolean safeResponse, int citationCount) {
        totalResponses.incrementAndGet();
        if (safeResponse) {
            failClosedResponses.incrementAndGet();
            return;
        }
        totalAnswerResponses.incrementAndGet();
        if (citationCount > 0) {
            answerResponsesWithCitation.incrementAndGet();
        }
    }

    public void recordSseFirstToken(long elapsedMs) {
        if (elapsedMs < 0) {
            return;
        }
        sseFirstTokenSeconds.record(Duration.ofMillis(elapsedMs));
    }

    public void recordIdempotencyRedisFallback() {
        idempotencyRedisFallbackTotal.incrementAndGet();
    }

    private double failClosedRate() {
        long total = totalResponses.get();
        if (total == 0) {
            return 0.0d;
        }
        return (double) failClosedResponses.get() / (double) total;
    }

    private double citationCoverage() {
        long totalAnswers = totalAnswerResponses.get();
        if (totalAnswers == 0) {
            return 0.0d;
        }
        return (double) answerResponsesWithCitation.get() / (double) totalAnswers;
    }

    private double idempotencyRedisFallbackTotal() {
        return idempotencyRedisFallbackTotal.get();
    }
}
