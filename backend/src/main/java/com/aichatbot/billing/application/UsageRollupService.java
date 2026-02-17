package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.domain.model.TenantDailyUsage;
import com.aichatbot.billing.domain.model.TenantMonthlyUsage;
import com.aichatbot.billing.domain.service.CostCalculator;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.billing.infrastructure.TenantUsageDailyRepository;
import com.aichatbot.billing.infrastructure.TenantUsageMonthlyRepository;
import com.aichatbot.global.observability.TraceContext;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UsageRollupService {

    private final GenerationLogRepository generationLogRepository;
    private final TenantUsageDailyRepository tenantUsageDailyRepository;
    private final TenantUsageMonthlyRepository tenantUsageMonthlyRepository;
    private final CostCalculator costCalculator;
    private final BillingMetrics billingMetrics;
    private final Clock clock;

    @Autowired
    public UsageRollupService(
        GenerationLogRepository generationLogRepository,
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics
    ) {
        this(
            generationLogRepository,
            tenantUsageDailyRepository,
            tenantUsageMonthlyRepository,
            costCalculator,
            billingMetrics,
            Clock.systemUTC()
        );
    }

    UsageRollupService(
        GenerationLogRepository generationLogRepository,
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics,
        Clock clock
    ) {
        this.generationLogRepository = generationLogRepository;
        this.tenantUsageDailyRepository = tenantUsageDailyRepository;
        this.tenantUsageMonthlyRepository = tenantUsageMonthlyRepository;
        this.costCalculator = costCalculator;
        this.billingMetrics = billingMetrics;
        this.clock = clock;
    }

    public void rollupDaily(LocalDate usageDate, String triggeredTraceId) {
        String traceId = resolveTraceId(triggeredTraceId);
        List<GenerationLogEntry> dailyEntries = generationLogRepository.findByDate(usageDate);
        Map<String, List<GenerationLogEntry>> grouped = dailyEntries.stream()
            .collect(Collectors.groupingBy(GenerationLogEntry::tenantId));

        Instant updatedAt = Instant.now(clock);
        for (Map.Entry<String, List<GenerationLogEntry>> entry : grouped.entrySet()) {
            String tenantId = entry.getKey();
            List<GenerationLogEntry> values = entry.getValue();
            long requestCount = values.size();
            long inputTokens = values.stream().mapToLong(GenerationLogEntry::inputTokens).sum();
            long outputTokens = values.stream().mapToLong(GenerationLogEntry::outputTokens).sum();
            long toolCalls = values.stream().mapToLong(GenerationLogEntry::toolCalls).sum();
            BigDecimal estimatedCost = costCalculator.sumCost(values);

            tenantUsageDailyRepository.save(new TenantDailyUsage(
                tenantId,
                usageDate,
                requestCount,
                inputTokens,
                outputTokens,
                toolCalls,
                estimatedCost,
                traceId,
                updatedAt
            ));
            billingMetrics.recordEstimatedCost(estimatedCost);
        }
    }

    public void rollupMonthly(YearMonth month, String triggeredTraceId) {
        String traceId = resolveTraceId(triggeredTraceId);
        Instant updatedAt = Instant.now(clock);
        LocalDate from = month.atDay(1);
        LocalDate to = month.atEndOfMonth();
        List<TenantDailyUsage> allDaily = tenantUsageDailyRepository.findAll().stream()
            .filter(usage -> !usage.usageDate().isBefore(from) && !usage.usageDate().isAfter(to))
            .toList();
        Map<String, List<TenantDailyUsage>> grouped = allDaily.stream()
            .collect(Collectors.groupingBy(TenantDailyUsage::tenantId));

        for (Map.Entry<String, List<TenantDailyUsage>> entry : grouped.entrySet()) {
            String tenantId = entry.getKey();
            List<TenantDailyUsage> values = entry.getValue();
            long requestCount = values.stream().mapToLong(TenantDailyUsage::requestCount).sum();
            long inputTokens = values.stream().mapToLong(TenantDailyUsage::inputTokens).sum();
            long outputTokens = values.stream().mapToLong(TenantDailyUsage::outputTokens).sum();
            long toolCalls = values.stream().mapToLong(TenantDailyUsage::toolCalls).sum();
            BigDecimal estimatedCost = values.stream()
                .map(TenantDailyUsage::estimatedCost)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

            tenantUsageMonthlyRepository.save(new TenantMonthlyUsage(
                tenantId,
                month,
                requestCount,
                inputTokens,
                outputTokens,
                toolCalls,
                estimatedCost,
                traceId,
                updatedAt
            ));
            billingMetrics.recordEstimatedCost(estimatedCost);
        }
    }

    public void rollupWindow(LocalDate from, LocalDate to, String triggeredTraceId) {
        LocalDate cursor = from;
        while (!cursor.isAfter(to)) {
            rollupDaily(cursor, triggeredTraceId);
            cursor = cursor.plusDays(1);
        }
        YearMonth startMonth = YearMonth.from(from);
        YearMonth endMonth = YearMonth.from(to);
        YearMonth monthCursor = startMonth;
        while (!monthCursor.isAfter(endMonth)) {
            rollupMonthly(monthCursor, triggeredTraceId);
            monthCursor = monthCursor.plusMonths(1);
        }
    }

    public void rollupPreviousDayAndCurrentMonth() {
        LocalDate previousDay = LocalDate.now(clock.withZone(ZoneOffset.UTC)).minusDays(1);
        rollupDaily(previousDay, UUID.randomUUID().toString());
        rollupMonthly(YearMonth.from(previousDay), UUID.randomUUID().toString());
    }

    private String resolveTraceId(String candidate) {
        if (candidate != null && !candidate.isBlank()) {
            return candidate;
        }
        String traceId = TraceContext.getTraceId();
        if (traceId != null && !traceId.isBlank()) {
            return traceId;
        }
        return UUID.randomUUID().toString();
    }
}
