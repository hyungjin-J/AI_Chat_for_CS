package com.aichatbot.ops.domain;

import java.time.Instant;
import java.util.UUID;

public record OpsEventAggregate(
    UUID tenantId,
    Instant hourBucketUtc,
    String metricKey,
    Long metricValue
) {
}
