package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.TenantQuota;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.stereotype.Repository;

@Repository
public class TenantQuotaRepository {

    private final Map<String, CopyOnWriteArrayList<TenantQuota>> quotaMap = new ConcurrentHashMap<>();

    public void upsert(TenantQuota quota) {
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.computeIfAbsent(quota.tenantId(), ignored -> new CopyOnWriteArrayList<>());
        quotas.removeIf(existing -> existing.effectiveFrom().equals(quota.effectiveFrom()));
        quotas.add(quota);
    }

    public Optional<TenantQuota> findActive(String tenantId, Instant at) {
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        if (quotas == null) {
            return Optional.empty();
        }
        return quotas.stream()
            .filter(quota -> quota.isEffectiveAt(at))
            .max(Comparator.comparing(TenantQuota::effectiveFrom));
    }

    public Optional<TenantQuota> findLatest(String tenantId) {
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        if (quotas == null) {
            return Optional.empty();
        }
        return quotas.stream().max(Comparator.comparing(TenantQuota::effectiveFrom));
    }

    public List<TenantQuota> findAll(String tenantId) {
        CopyOnWriteArrayList<TenantQuota> quotas = quotaMap.get(tenantId);
        return quotas == null ? List.of() : List.copyOf(quotas);
    }

    public void clear() {
        quotaMap.clear();
    }
}

