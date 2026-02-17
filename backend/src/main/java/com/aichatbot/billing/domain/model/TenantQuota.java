package com.aichatbot.billing.domain.model;

import java.math.BigDecimal;
import java.time.Instant;

public record TenantQuota(
    String tenantId,
    int maxQps,
    long maxDailyTokens,
    BigDecimal maxMonthlyCost,
    Instant effectiveFrom,
    Instant effectiveTo,
    BreachAction breachAction,
    String updatedBy,
    String traceId,
    Instant updatedAt
) {

    public boolean isEffectiveAt(Instant at) {
        boolean fromSatisfied = !effectiveFrom.isAfter(at);
        boolean toSatisfied = effectiveTo == null || effectiveTo.isAfter(at);
        return fromSatisfied && toSatisfied;
    }
}

