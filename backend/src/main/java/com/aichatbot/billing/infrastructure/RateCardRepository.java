package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.CostRateCard;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.stereotype.Repository;

@Repository
public class RateCardRepository {

    private final CopyOnWriteArrayList<CostRateCard> rateCards = new CopyOnWriteArrayList<>();

    public void save(CostRateCard rateCard) {
        rateCards.add(rateCard);
    }

    public Optional<CostRateCard> findApplicable(String providerId, String modelId, Instant at) {
        return rateCards.stream()
            .filter(card -> card.matchesModel(providerId, modelId))
            .filter(card -> card.isEffectiveAt(at))
            .max(Comparator.comparing(CostRateCard::effectiveFrom));
    }

    public List<CostRateCard> findAll() {
        return new ArrayList<>(rateCards);
    }

    public void clear() {
        rateCards.clear();
    }
}

