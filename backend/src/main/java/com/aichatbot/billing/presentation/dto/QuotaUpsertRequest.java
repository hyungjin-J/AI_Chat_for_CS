package com.aichatbot.billing.presentation.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.math.BigDecimal;
import java.time.Instant;

public record QuotaUpsertRequest(
    @PositiveOrZero
    int maxQps,
    @PositiveOrZero
    long maxDailyTokens,
    @NotNull
    @DecimalMin(value = "0.0")
    BigDecimal maxMonthlyCost,
    @NotNull
    Instant effectiveFrom,
    Instant effectiveTo,
    String breachAction
) {
}

