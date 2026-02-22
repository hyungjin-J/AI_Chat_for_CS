package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.TenantSubscriptionMapper;
import com.aichatbot.contexts.billing.domain.model.TenantSubscription;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class TenantSubscriptionRepository {

    private final TenantSubscriptionMapper tenantSubscriptionMapper;
    private final String persistenceMode;
    private final Map<String, TenantSubscription> subscriptionMap = new ConcurrentHashMap<>();

    public TenantSubscriptionRepository() {
        this.tenantSubscriptionMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public TenantSubscriptionRepository(
        @Autowired(required = false) TenantSubscriptionMapper tenantSubscriptionMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.tenantSubscriptionMapper = tenantSubscriptionMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(TenantSubscription subscription) {
        if (useMapperPersistence()) {
            tenantSubscriptionMapper.deleteByTenant(subscription.tenantId());
            tenantSubscriptionMapper.insert(
                subscription.tenantId(),
                subscription.planCode(),
                subscription.status(),
                subscription.startedAt(),
                subscription.endedAt()
            );
            return;
        }
        subscriptionMap.put(subscription.tenantId(), subscription);
    }

    public Optional<TenantSubscription> findActive(String tenantId, Instant at) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(tenantSubscriptionMapper.findActive(tenantId, at));
        }
        TenantSubscription subscription = subscriptionMap.get(tenantId);
        if (subscription == null || !subscription.isActiveAt(at)) {
            return Optional.empty();
        }
        return Optional.of(subscription);
    }

    public Optional<TenantSubscription> findLatest(String tenantId) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(tenantSubscriptionMapper.findLatest(tenantId));
        }
        return Optional.ofNullable(subscriptionMap.get(tenantId));
    }

    public void clear() {
        if (useMapperPersistence()) {
            tenantSubscriptionMapper.deleteAll();
            return;
        }
        subscriptionMap.clear();
    }

    private boolean useMapperPersistence() {
        return tenantSubscriptionMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }
}


