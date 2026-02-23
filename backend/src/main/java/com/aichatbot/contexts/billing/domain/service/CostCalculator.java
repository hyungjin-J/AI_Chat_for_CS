package com.aichatbot.contexts.billing.domain.service;

import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import com.aichatbot.contexts.billing.domain.model.GenerationLogEntry;
import com.aichatbot.contexts.billing.domain.port.RateCardLookup;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class CostCalculator {

    private static final BigDecimal ONE_THOUSAND = new BigDecimal("1000");

    private final RateCardLookup rateCardLookup;

    public CostCalculator(RateCardLookup rateCardLookup) {
        this.rateCardLookup = rateCardLookup;
    }

    public BigDecimal estimateCost(GenerationLogEntry entry) {
        Optional<CostRateCard> rateCard = rateCardLookup.findApplicable(
            entry.providerId(),
            entry.modelId(),
            entry.createdAt()
        );
        return rateCard.map(card -> estimateCost(entry, card)).orElse(BigDecimal.ZERO);
    }

    public BigDecimal estimateCostForProjectedRequest(
        String providerId,
        String modelId,
        Instant at,
        int inputTokens,
        int outputTokens,
        int toolCalls
    ) {
        Optional<CostRateCard> rateCard = rateCardLookup.findApplicable(providerId, modelId, at);
        if (rateCard.isEmpty()) {
            return BigDecimal.ZERO;
        }
        CostRateCard card = rateCard.get();
        BigDecimal inputCost = card.inputTokenCostPer1k()
            .multiply(BigDecimal.valueOf(inputTokens))
            .divide(ONE_THOUSAND, 6, RoundingMode.HALF_UP);
        BigDecimal outputCost = card.outputTokenCostPer1k()
            .multiply(BigDecimal.valueOf(outputTokens))
            .divide(ONE_THOUSAND, 6, RoundingMode.HALF_UP);
        BigDecimal toolCost = card.toolCallCost().multiply(BigDecimal.valueOf(toolCalls));
        return inputCost.add(outputCost).add(toolCost).setScale(6, RoundingMode.HALF_UP);
    }

    public BigDecimal sumCost(List<GenerationLogEntry> entries) {
        return entries.stream()
            .map(this::estimateCost)
            .reduce(BigDecimal.ZERO, BigDecimal::add)
            .setScale(6, RoundingMode.HALF_UP);
    }

    private BigDecimal estimateCost(GenerationLogEntry entry, CostRateCard card) {
        BigDecimal inputCost = card.inputTokenCostPer1k()
            .multiply(BigDecimal.valueOf(entry.inputTokens()))
            .divide(ONE_THOUSAND, 6, RoundingMode.HALF_UP);
        BigDecimal outputCost = card.outputTokenCostPer1k()
            .multiply(BigDecimal.valueOf(entry.outputTokens()))
            .divide(ONE_THOUSAND, 6, RoundingMode.HALF_UP);
        BigDecimal toolCost = card.toolCallCost().multiply(BigDecimal.valueOf(entry.toolCalls()));
        return inputCost.add(outputCost).add(toolCost).setScale(6, RoundingMode.HALF_UP);
    }
}


