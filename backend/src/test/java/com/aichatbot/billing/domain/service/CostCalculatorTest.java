package com.aichatbot.billing.domain.service;

import com.aichatbot.billing.domain.model.CostRateCard;
import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.infrastructure.RateCardRepository;
import java.math.BigDecimal;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class CostCalculatorTest {

    private RateCardRepository rateCardRepository;
    private CostCalculator costCalculator;

    @BeforeEach
    void setUp() {
        rateCardRepository = new RateCardRepository();
        costCalculator = new CostCalculator(rateCardRepository);
    }

    @Test
    void shouldUseRateCardByEffectiveWindow() {
        rateCardRepository.save(new CostRateCard(
            "rate-old",
            "provider-a",
            "model-a",
            new BigDecimal("0.001"),
            new BigDecimal("0.002"),
            new BigDecimal("0.010"),
            Instant.parse("2026-01-01T00:00:00Z"),
            Instant.parse("2026-02-15T00:00:00Z")
        ));
        rateCardRepository.save(new CostRateCard(
            "rate-new",
            "provider-a",
            "model-a",
            new BigDecimal("0.003"),
            new BigDecimal("0.004"),
            new BigDecimal("0.020"),
            Instant.parse("2026-02-15T00:00:00Z"),
            null
        ));

        GenerationLogEntry oldPeriodEntry = new GenerationLogEntry(
            "g1",
            "tenant-a",
            "m1",
            "provider-a",
            "model-a",
            1000,
            500,
            1,
            "masked",
            "trace-1",
            Instant.parse("2026-02-10T10:00:00Z")
        );
        GenerationLogEntry newPeriodEntry = new GenerationLogEntry(
            "g2",
            "tenant-a",
            "m2",
            "provider-a",
            "model-a",
            1000,
            500,
            1,
            "masked",
            "trace-2",
            Instant.parse("2026-02-20T10:00:00Z")
        );

        BigDecimal oldCost = costCalculator.estimateCost(oldPeriodEntry);
        BigDecimal newCost = costCalculator.estimateCost(newPeriodEntry);

        assertThat(oldCost).isEqualByComparingTo(new BigDecimal("0.012000"));
        assertThat(newCost).isEqualByComparingTo(new BigDecimal("0.025000"));
    }
}

