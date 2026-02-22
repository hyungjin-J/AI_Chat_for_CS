package com.aichatbot.contexts.billing.infrastructure;

import java.math.BigDecimal;
import java.time.Instant;

public record TenantQuotaRow(
    String tenantId,
    Integer maxQps,
    Long maxDailyTokens,
    BigDecimal maxMonthlyCost,
    Instant effectiveFrom,
    Instant effectiveTo,
    String breachAction,
    String updatedBy,
    String traceId,
    Instant updatedAt
) {
}
