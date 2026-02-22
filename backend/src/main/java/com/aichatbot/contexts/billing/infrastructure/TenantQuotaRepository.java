package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.TenantQuotaMapper;
import com.aichatbot.contexts.billing.domain.model.BreachAction;
import com.aichatbot.contexts.billing.domain.model.TenantQuota;
import com.aichatbot.contexts.billing.domain.readmodel.TenantQuotaRow;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class TenantQuotaRepository {

    private final TenantQuotaMapper tenantQuotaMapper;
    private final String persistenceMode;
    private final Map<String, CopyOnWriteArrayList<TenantQuota>> quotaMap = new ConcurrentHashMap<>();

    public TenantQuotaRepository() {
        this.tenantQuotaMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public TenantQuotaRepository(
        @Autowired(required = false) TenantQuotaMapper tenantQuotaMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.tenantQuotaMapper = tenantQuotaMapper;
        this.persistenceMode = persistenceMode;
    }

    public void upsert(TenantQuota quota) {
        if (useMapperPersistence()) {
            tenantQuotaMapper.deleteByTenantAndEffectiveFrom(quota.tenantId(), quota.effectiveFrom());
            tenantQuotaMapper.insert(
                quota.tenantId(),
                quota.maxQps(),
                quota.maxDailyTokens(),
                quota.maxMonthlyCost(),
                quota.effectiveFrom(),
                quota.effectiveTo(),
                quota.breachAction().name(),
                quota.updatedBy(),
                quota.traceId(),
                quota.updatedAt()
            );
            return;
        }
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.computeIfAbsent(quota.tenantId(), ignored -> new CopyOnWriteArrayList<>());
        quotas.removeIf(existing -> existing.effectiveFrom().equals(quota.effectiveFrom()));
        quotas.add(quota);
    }

    public Optional<TenantQuota> findActive(String tenantId, Instant at) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(toDomain(tenantQuotaMapper.findActive(tenantId, at)));
        }
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        if (quotas == null) {
            return Optional.empty();
        }
        return quotas.stream()
            .filter(quota -> quota.isEffectiveAt(at))
            .max(Comparator.comparing(TenantQuota::effectiveFrom));
    }

    public Optional<TenantQuota> findLatest(String tenantId) {
        if (useMapperPersistence()) {
            return Optional.ofNullable(toDomain(tenantQuotaMapper.findLatest(tenantId)));
        }
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        if (quotas == null) {
            return Optional.empty();
        }
        return quotas.stream().max(Comparator.comparing(TenantQuota::effectiveFrom));
    }

    public List<TenantQuota> findAll(String tenantId) {
        if (useMapperPersistence()) {
            return tenantQuotaMapper.findAll(tenantId).stream().map(this::toDomain).toList();
        }
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        return quotas == null ? List.of() : List.copyOf(quotas);
    }

    public void clear() {
        if (useMapperPersistence()) {
            tenantQuotaMapper.deleteAll();
            return;
        }
        quotaMap.clear();
    }

    private boolean useMapperPersistence() {
        return tenantQuotaMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }

    private TenantQuota toDomain(TenantQuotaRow row) {
        if (row == null) {
            return null;
        }
        return new TenantQuota(
            row.tenantId(),
            row.maxQps(),
            row.maxDailyTokens(),
            row.maxMonthlyCost(),
            row.effectiveFrom(),
            row.effectiveTo(),
            BreachAction.valueOf(row.breachAction()),
            row.updatedBy(),
            row.traceId(),
            row.updatedAt()
        );
    }
}


