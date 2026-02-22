package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.RateCardMapper;
import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class RateCardRepository {

    private final RateCardMapper rateCardMapper;
    private final String persistenceMode;
    private final CopyOnWriteArrayList<CostRateCard> rateCards = new CopyOnWriteArrayList<>();

    public RateCardRepository() {
        this.rateCardMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public RateCardRepository(
        @Autowired(required = false) RateCardMapper rateCardMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.rateCardMapper = rateCardMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(CostRateCard rateCard) {
        if (useMapperPersistence()) {
            rateCardMapper.insert(
                rateCard.rateCardId(),
                rateCard.providerId(),
                rateCard.modelId(),
                rateCard.inputTokenCostPer1k(),
                rateCard.outputTokenCostPer1k(),
                rateCard.toolCallCost(),
                rateCard.effectiveFrom(),
                rateCard.effectiveTo()
            );
            return;
        }
        rateCards.add(rateCard);
    }

    public Optional<CostRateCard> findApplicable(String providerId, String modelId, Instant at) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(rateCardMapper.findApplicable(providerId, modelId, at));
        }
        return rateCards.stream()
            .filter(card -> card.matchesModel(providerId, modelId))
            .filter(card -> card.isEffectiveAt(at))
            .max(Comparator.comparing(CostRateCard::effectiveFrom));
    }

    public List<CostRateCard> findAll() {
        if (useMapperPersistence()) {
            return rateCardMapper.findAll();
        }
        return new ArrayList<>(rateCards);
    }

    public void clear() {
        if (useMapperPersistence()) {
            rateCardMapper.deleteAll();
            return;
        }
        rateCards.clear();
    }

    private boolean useMapperPersistence() {
        return rateCardMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }
}


