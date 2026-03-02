package com.aichatbot.contexts.operations.domain;

import java.time.Instant;
import java.util.UUID;

public record OpsTraceRow(
    UUID id,
    UUID traceId,
    String eventType,
    String metricKey,
    Long metricValue,
    String dimensionsJson,
    Instant eventTime
) {
}
