package com.aichatbot.contexts.billing.infrastructure;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

public record TenantDailyUsageRow(
    String tenantId,
    LocalDate usageDate,
    Long requestCount,
    Long inputTokens,
    Long outputTokens,
    Long toolCalls,
    BigDecimal estimatedCost,
    String traceId,
    Instant updatedAt
) {
}
