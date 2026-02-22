package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.TenantUsageDailyMapper;
import com.aichatbot.contexts.billing.domain.model.TenantDailyUsage;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class TenantUsageDailyRepository {

    private final TenantUsageDailyMapper tenantUsageDailyMapper;
    private final String persistenceMode;
    private final Map<String, TenantDailyUsage> usageMap = new ConcurrentHashMap<>();

    public TenantUsageDailyRepository() {
        this.tenantUsageDailyMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public TenantUsageDailyRepository(
        @Autowired(required = false) TenantUsageDailyMapper tenantUsageDailyMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.tenantUsageDailyMapper = tenantUsageDailyMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(TenantDailyUsage usage) {
        if (useMapperPersistence()) {
            tenantUsageDailyMapper.deleteByTenantAndDate(usage.tenantId(), usage.usageDate());
            tenantUsageDailyMapper.insert(
                usage.tenantId(),
                usage.usageDate(),
                usage.requestCount(),
                usage.inputTokens(),
                usage.outputTokens(),
                usage.toolCalls(),
                usage.estimatedCost(),
                usage.traceId(),
                usage.updatedAt()
            );
            return;
        }
        usageMap.put(key(usage.tenantId(), usage.usageDate()), usage);
    }

    public TenantDailyUsage findOne(String tenantId, LocalDate usageDate) {
        if (useMapperPersistence()) {
            return toDomain(tenantUsageDailyMapper.findOne(tenantId, usageDate));
        }
        return usageMap.get(key(tenantId, usageDate));
    }

    public List<TenantDailyUsage> findByTenantAndDateRange(String tenantId, LocalDate from, LocalDate to) {
        if (useMapperPersistence()) {
            return tenantUsageDailyMapper.findByTenantAndDateRange(tenantId, from, to).stream()
                .map(this::toDomain)
                .toList();
        }
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> !usage.usageDate().isBefore(from) && !usage.usageDate().isAfter(to))
            .sorted((left, right) -> left.usageDate().compareTo(right.usageDate()))
            .toList();
    }

    public List<TenantDailyUsage> findByMonth(String tenantId, int year, int month) {
        if (useMapperPersistence()) {
            LocalDate monthFrom = LocalDate.of(year, month, 1);
            LocalDate monthTo = monthFrom.withDayOfMonth(monthFrom.lengthOfMonth());
            return tenantUsageDailyMapper.findByMonth(tenantId, monthFrom, monthTo).stream()
                .map(this::toDomain)
                .toList();
        }
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> usage.usageDate().getYear() == year && usage.usageDate().getMonthValue() == month)
            .toList();
    }

    public List<TenantDailyUsage> findAll() {
        if (useMapperPersistence()) {
            return tenantUsageDailyMapper.findAll().stream().map(this::toDomain).toList();
        }
        return usageMap.values().stream().toList();
    }

    public void clear() {
        if (useMapperPersistence()) {
            tenantUsageDailyMapper.deleteAll();
            return;
        }
        usageMap.clear();
    }

    private String key(String tenantId, LocalDate date) {
        return tenantId + "|" + date;
    }

    private boolean useMapperPersistence() {
        return tenantUsageDailyMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }

    private TenantDailyUsage toDomain(TenantDailyUsageRow row) {
        if (row == null) {
            return null;
        }
        return new TenantDailyUsage(
            row.tenantId(),
            row.usageDate(),
            row.requestCount(),
            row.inputTokens(),
            row.outputTokens(),
            row.toolCalls(),
            row.estimatedCost(),
            row.traceId(),
            row.updatedAt()
        );
    }
}


