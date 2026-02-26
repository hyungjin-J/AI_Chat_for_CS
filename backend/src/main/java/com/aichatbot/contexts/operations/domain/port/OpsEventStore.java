package com.aichatbot.contexts.operations.domain.port;

import java.time.Instant;
import java.util.UUID;

public interface OpsEventStore {

    void insertOpsEvent(
        UUID id,
        UUID tenantId,
        UUID traceId,
        Instant eventTime,
        String eventType,
        String metricKey,
        long metricValue,
        String dimensionsJson
    );
}
