package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.TenantSubscription;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class TenantSubscriptionRepository {

    private final Map<String, TenantSubscription> subscriptionMap = new ConcurrentHashMap<>();

    public void save(TenantSubscription subscription) {
        subscriptionMap.put(subscription.tenantId(), subscription);
    }

    public Optional<TenantSubscription> findActive(String tenantId, Instant at) {
        TenantSubscription subscription = subscriptionMap.get(tenantId);
        if (subscription == null || !subscription.isActiveAt(at)) {
            return Optional.empty();
        }
        return Optional.of(subscription);
    }

    public Optional<TenantSubscription> findLatest(String tenantId) {
        return Optional.ofNullable(subscriptionMap.get(tenantId));
    }

    public void clear() {
        subscriptionMap.clear();
    }
}

