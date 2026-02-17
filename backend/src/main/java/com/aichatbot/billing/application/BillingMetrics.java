package com.aichatbot.billing.application;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.math.BigDecimal;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.stereotype.Component;

@Component
public class BillingMetrics {

    private final Counter quotaBreachCount;
    private final Counter tokenBudgetExceededCount;
    private final AtomicReference<Double> estimatedCostValue = new AtomicReference<>(0.0d);

    public BillingMetrics(MeterRegistry meterRegistry) {
        this.quotaBreachCount = Counter.builder("quota_breach_count")
            .description("Number of quota breach events")
            .register(meterRegistry);
        this.tokenBudgetExceededCount = Counter.builder("token_budget_exceeded_count")
            .description("Number of token budget exceeded events")
            .register(meterRegistry);
        Gauge.builder("estimated_cost", estimatedCostValue, AtomicReference::get)
            .description("Latest estimated tenant cost")
            .register(meterRegistry);
    }

    public void recordEstimatedCost(BigDecimal estimatedCost) {
        estimatedCostValue.set(estimatedCost.doubleValue());
    }

    public void incrementQuotaBreach() {
        quotaBreachCount.increment();
    }

    public void incrementTokenBudgetExceeded() {
        tokenBudgetExceededCount.increment();
    }
}

