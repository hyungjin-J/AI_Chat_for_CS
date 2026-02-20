package com.aichatbot.rag.application;

import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

@Component
public class RagRetrievalMetrics {

    private final Timer ragSearchMs;
    private final Timer bm25Ms;
    private final Timer vectorMs;
    private final Timer rrfMs;
    private final Timer rerankMs;
    private final AtomicLong totalRequests = new AtomicLong();
    private final AtomicLong zeroEvidenceRequests = new AtomicLong();

    public RagRetrievalMetrics(MeterRegistry meterRegistry) {
        this.ragSearchMs = Timer.builder("rag_search_ms").register(meterRegistry);
        this.bm25Ms = Timer.builder("bm25_ms").register(meterRegistry);
        this.vectorMs = Timer.builder("vector_ms").register(meterRegistry);
        this.rrfMs = Timer.builder("rrf_ms").register(meterRegistry);
        this.rerankMs = Timer.builder("rerank_ms").register(meterRegistry);
        Gauge.builder("zero_evidence_rate", this, RagRetrievalMetrics::zeroEvidenceRate).register(meterRegistry);
    }

    public void recordRagSearch(long elapsedMs) {
        ragSearchMs.record(Duration.ofMillis(Math.max(0, elapsedMs)));
    }

    public void recordBm25(long elapsedMs) {
        bm25Ms.record(Duration.ofMillis(Math.max(0, elapsedMs)));
    }

    public void recordVector(long elapsedMs) {
        vectorMs.record(Duration.ofMillis(Math.max(0, elapsedMs)));
    }

    public void recordRrf(long elapsedMs) {
        rrfMs.record(Duration.ofMillis(Math.max(0, elapsedMs)));
    }

    public void recordRerank(long elapsedMs) {
        rerankMs.record(Duration.ofMillis(Math.max(0, elapsedMs)));
    }

    public void recordOutcome(boolean zeroEvidence) {
        totalRequests.incrementAndGet();
        if (zeroEvidence) {
            zeroEvidenceRequests.incrementAndGet();
        }
    }

    private double zeroEvidenceRate() {
        long total = totalRequests.get();
        if (total == 0L) {
            return 0.0d;
        }
        return (double) zeroEvidenceRequests.get() / (double) total;
    }
}
