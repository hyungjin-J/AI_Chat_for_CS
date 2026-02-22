package com.aichatbot.platform.idempotency;

public interface IdempotencyFallbackMetricsRecorder {
    void recordRedisFallback();
}
