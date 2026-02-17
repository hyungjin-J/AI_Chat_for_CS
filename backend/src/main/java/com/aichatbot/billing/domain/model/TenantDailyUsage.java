package com.aichatbot.billing.domain.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

public record TenantDailyUsage(
    String tenantId,
    LocalDate usageDate,
    long requestCount,
    long inputTokens,
    long outputTokens,
    long toolCalls,
    BigDecimal estimatedCost,
    String traceId,
    Instant updatedAt
) {
}

