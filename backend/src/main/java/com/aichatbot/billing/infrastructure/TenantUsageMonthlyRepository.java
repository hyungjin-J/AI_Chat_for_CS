package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.TenantMonthlyUsage;
import java.time.YearMonth;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class TenantUsageMonthlyRepository {

    private final Map<String, TenantMonthlyUsage> usageMap = new ConcurrentHashMap<>();

    public void save(TenantMonthlyUsage usage) {
        usageMap.put(key(usage.tenantId(), usage.usageMonth()), usage);
    }

    public TenantMonthlyUsage findOne(String tenantId, YearMonth usageMonth) {
        return usageMap.get(key(tenantId, usageMonth));
    }

    public List<TenantMonthlyUsage> findByTenantAndMonthRange(String tenantId, YearMonth from, YearMonth to) {
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> !usage.usageMonth().isBefore(from) && !usage.usageMonth().isAfter(to))
            .sorted((left, right) -> left.usageMonth().compareTo(right.usageMonth()))
            .toList();
    }

    public List<TenantMonthlyUsage> findAll() {
        return usageMap.values().stream().toList();
    }

    public void clear() {
        usageMap.clear();
    }

    private String key(String tenantId, YearMonth month) {
        return tenantId + "|" + month;
    }
}

