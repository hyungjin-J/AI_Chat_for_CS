package com.aichatbot.contexts.conversation.message.application;

import com.aichatbot.platform.idempotency.IdempotencyFallbackMetricsRecorder;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Component;

@Component
@Primary
public class IdempotencyFallbackMetricsAdapter implements IdempotencyFallbackMetricsRecorder {

    private final MvpObservabilityMetrics mvpObservabilityMetrics;

    public IdempotencyFallbackMetricsAdapter(MvpObservabilityMetrics mvpObservabilityMetrics) {
        this.mvpObservabilityMetrics = mvpObservabilityMetrics;
    }

    @Override
    public void recordRedisFallback() {
        mvpObservabilityMetrics.recordIdempotencyRedisFallback();
    }
}
