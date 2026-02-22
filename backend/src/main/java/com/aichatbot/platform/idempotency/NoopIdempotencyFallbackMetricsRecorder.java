package com.aichatbot.platform.idempotency;

import org.springframework.stereotype.Component;

@Component
public class NoopIdempotencyFallbackMetricsRecorder implements IdempotencyFallbackMetricsRecorder {
    @Override
    public void recordRedisFallback() {
        // No-op fallback to keep platform layer independent from domain metrics.
    }
}
