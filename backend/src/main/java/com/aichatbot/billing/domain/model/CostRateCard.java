package com.aichatbot.billing.domain.model;

import java.math.BigDecimal;
import java.time.Instant;

public record CostRateCard(
    String rateCardId,
    String providerId,
    String modelId,
    BigDecimal inputTokenCostPer1k,
    BigDecimal outputTokenCostPer1k,
    BigDecimal toolCallCost,
    Instant effectiveFrom,
    Instant effectiveTo
) {

    public boolean isEffectiveAt(Instant at) {
        boolean fromSatisfied = !effectiveFrom.isAfter(at);
        boolean toSatisfied = effectiveTo == null || effectiveTo.isAfter(at);
        return fromSatisfied && toSatisfied;
    }

    public boolean matchesModel(String provider, String model) {
        return providerId.equals(provider) && modelId.equals(model);
    }
}

