package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.domain.mapper.TenantUsageMonthlyMapper;
import com.aichatbot.contexts.billing.domain.model.TenantMonthlyUsage;
import com.aichatbot.contexts.billing.domain.model.TenantMonthlyUsageRow;
import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

@Repository
public class TenantUsageMonthlyRepository {

    private final TenantUsageMonthlyMapper tenantUsageMonthlyMapper;
    private final String persistenceMode;
    private final Map<String, TenantMonthlyUsage> usageMap = new ConcurrentHashMap<>();

    public TenantUsageMonthlyRepository() {
        this.tenantUsageMonthlyMapper = null;
        this.persistenceMode = "memory";
    }

    @Autowired
    public TenantUsageMonthlyRepository(
        @Autowired(required = false) TenantUsageMonthlyMapper tenantUsageMonthlyMapper,
        @Value("${app.billing.persistence.mode:mybatis}") String persistenceMode
    ) {
        this.tenantUsageMonthlyMapper = tenantUsageMonthlyMapper;
        this.persistenceMode = persistenceMode;
    }

    public void save(TenantMonthlyUsage usage) {
        if (useMapperPersistence()) {
            LocalDate usageMonthDate = usage.usageMonth().atDay(1);
            tenantUsageMonthlyMapper.deleteByTenantAndMonth(usage.tenantId(), usageMonthDate);
            tenantUsageMonthlyMapper.insert(
                usage.tenantId(),
                usageMonthDate,
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
        usageMap.put(key(usage.tenantId(), usage.usageMonth()), usage);
    }

    public TenantMonthlyUsage findOne(String tenantId, YearMonth usageMonth) {
        if (useMapperPersistence()) {
            return toDomain(tenantUsageMonthlyMapper.findOne(tenantId, usageMonth.atDay(1)));
        }
        return usageMap.get(key(tenantId, usageMonth));
    }

    public List<TenantMonthlyUsage> findByTenantAndMonthRange(String tenantId, YearMonth from, YearMonth to) {
        if (useMapperPersistence()) {
            return tenantUsageMonthlyMapper.findByTenantAndMonthRange(
                    tenantId,
                    from.atDay(1),
                    to.atDay(1)
                ).stream()
                .map(this::toDomain)
                .toList();
        }
        return usageMap.values().stream()
            .filter(usage -> usage.tenantId().equals(tenantId))
            .filter(usage -> !usage.usageMonth().isBefore(from) && !usage.usageMonth().isAfter(to))
            .sorted((left, right) -> left.usageMonth().compareTo(right.usageMonth()))
            .toList();
    }

    public List<TenantMonthlyUsage> findAll() {
        if (useMapperPersistence()) {
            return tenantUsageMonthlyMapper.findAll().stream().map(this::toDomain).toList();
        }
        return usageMap.values().stream().toList();
    }

    public void clear() {
        if (useMapperPersistence()) {
            tenantUsageMonthlyMapper.deleteAll();
            return;
        }
        usageMap.clear();
    }

    private String key(String tenantId, YearMonth month) {
        return tenantId + "|" + month;
    }

    private TenantMonthlyUsage toDomain(TenantMonthlyUsageRow row) {
        if (row == null) {
            return null;
        }
        return new TenantMonthlyUsage(
            row.tenantId(),
            YearMonth.from(row.usageMonthDate()),
            row.requestCount(),
            row.inputTokens(),
            row.outputTokens(),
            row.toolCalls(),
            row.estimatedCost(),
            row.traceId(),
            row.updatedAt()
        );
    }

    private boolean useMapperPersistence() {
        return tenantUsageMonthlyMapper != null && "mybatis".equalsIgnoreCase(persistenceMode);
    }
}


