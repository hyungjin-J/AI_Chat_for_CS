package com.aichatbot.billing.domain.model;

import java.time.Instant;

public record TenantSubscription(
    String tenantId,
    String planCode,
    String status,
    Instant startedAt,
    Instant endedAt
) {

    public boolean isActiveAt(Instant at) {
        boolean starts = !startedAt.isAfter(at);
        boolean ends = endedAt == null || endedAt.isAfter(at);
        return starts && ends && "ACTIVE".equalsIgnoreCase(status);
    }
}

