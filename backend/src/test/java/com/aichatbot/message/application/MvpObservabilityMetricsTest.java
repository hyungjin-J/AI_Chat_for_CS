package com.aichatbot.message.application;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class MvpObservabilityMetricsTest {

    @Test
    void shouldExposeFailClosedRateAndCitationCoverage() {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        MvpObservabilityMetrics metrics = new MvpObservabilityMetrics(meterRegistry);

        metrics.recordGenerationOutcome(true, 0);
        metrics.recordGenerationOutcome(false, 1);
        metrics.recordGenerationOutcome(false, 0);

        Double failClosedRate = meterRegistry.get("fail_closed_rate").gauge().value();
        Double citationCoverage = meterRegistry.get("citation_coverage").gauge().value();

        assertThat(failClosedRate).isEqualTo(1.0d / 3.0d);
        assertThat(citationCoverage).isEqualTo(0.5d);
    }
}

