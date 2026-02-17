package com.aichatbot.billing.domain.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.YearMonth;

public record TenantMonthlyUsage(
    String tenantId,
    YearMonth usageMonth,
    long requestCount,
    long inputTokens,
    long outputTokens,
    long toolCalls,
    BigDecimal estimatedCost,
    String traceId,
    Instant updatedAt
) {
}

