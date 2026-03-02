package com.aichatbot.contexts.knowledge.rag.application;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

@Component
public class KbIndexPipelineMetrics {

    private final Timer kbIndexLatencyMs;
    private final AtomicLong totalJobs = new AtomicLong();
    private final AtomicLong failedJobs = new AtomicLong();
    private final AtomicLong parserFailures = new AtomicLong();

    public KbIndexPipelineMetrics(MeterRegistry meterRegistry) {
        this.kbIndexLatencyMs = Timer.builder("kb_index_latency_ms")
            .description("KB indexing pipeline latency in milliseconds")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(meterRegistry);

        Gauge.builder("kb_index_fail_rate", this, KbIndexPipelineMetrics::kbIndexFailRate)
            .description("Ratio of failed KB index jobs")
            .register(meterRegistry);

        Gauge.builder("parser_error_rate", this, KbIndexPipelineMetrics::parserErrorRate)
            .description("Ratio of parser stage failures among KB index jobs")
            .register(meterRegistry);
    }

    public void recordSuccess(long elapsedMs) {
        totalJobs.incrementAndGet();
        kbIndexLatencyMs.record(Duration.ofMillis(Math.max(0L, elapsedMs)));
    }

    public void recordFailure(long elapsedMs, boolean parserFailure) {
        totalJobs.incrementAndGet();
        failedJobs.incrementAndGet();
        if (parserFailure) {
            parserFailures.incrementAndGet();
        }
        kbIndexLatencyMs.record(Duration.ofMillis(Math.max(0L, elapsedMs)));
    }

    private double kbIndexFailRate() {
        long total = totalJobs.get();
        if (total <= 0L) {
            return 0.0d;
        }
        return (double) failedJobs.get() / (double) total;
    }

    private double parserErrorRate() {
        long total = totalJobs.get();
        if (total <= 0L) {
            return 0.0d;
        }
        return (double) parserFailures.get() / (double) total;
    }
}
