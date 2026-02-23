package com.aichatbot.contexts.billing.domain.port;

import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import java.time.Instant;
import java.util.Optional;

public abstract class RateCardLookup {

    public abstract Optional<CostRateCard> findApplicable(String providerId, String modelId, Instant at);
}
