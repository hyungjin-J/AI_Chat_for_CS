package com.aichatbot.billing.infrastructure;

import com.aichatbot.billing.domain.model.TenantDailyUsage;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class TenantUsageDailyRepository {

    private final Map<String, TenantDailyUsage> usageMap = new ConcurrentHashMap<>();

    public void save(TenantDailyUsage usage) {
        usageMap.put(key(usage.tenantId(), usage.usageDate()), usage);
    }

    public TenantDailyUsage findOne(String tenantId, LocalDate usageDate) {
        return usageMap.get(key(tenantId, usageDate));
    }

    public List<TenantDailyUsage> findByTenantAndDateRange(String tenantId, LocalDate from, LocalDate to) {
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> !usage.usageDate().isBefore(from) && !usage.usageDate().isAfter(to))
            .sorted((left, right) -> left.usageDate().compareTo(right.usageDate()))
            .toList();
    }

    public List<TenantDailyUsage> findByMonth(String tenantId, int year, int month) {
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> usage.usageDate().getYear() == year && usage.usageDate().getMonthValue() == month)
            .toList();
    }

    public List<TenantDailyUsage> findAll() {
        return usageMap.values().stream().toList();
    }

    public void clear() {
        usageMap.clear();
    }

    private String key(String tenantId, LocalDate date) {
        return tenantId + "|" + date;
    }
}

