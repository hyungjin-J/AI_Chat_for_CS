package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.BreachAction;
import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.domain.model.TenantDailyUsage;
import com.aichatbot.billing.domain.model.TenantMonthlyUsage;
import com.aichatbot.billing.domain.model.TenantPlan;
import com.aichatbot.billing.domain.model.TenantQuota;
import com.aichatbot.billing.domain.model.TenantSubscription;
import com.aichatbot.billing.domain.service.CostCalculator;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.billing.infrastructure.TenantPlanRepository;
import com.aichatbot.billing.infrastructure.TenantQuotaRepository;
import com.aichatbot.billing.infrastructure.TenantSubscriptionRepository;
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
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UsageReportService {

    private final TenantUsageDailyRepository tenantUsageDailyRepository;
    private final TenantUsageMonthlyRepository tenantUsageMonthlyRepository;
    private final TenantQuotaRepository tenantQuotaRepository;
    private final TenantSubscriptionRepository tenantSubscriptionRepository;
    private final TenantPlanRepository tenantPlanRepository;
    private final GenerationLogRepository generationLogRepository;
    private final CostCalculator costCalculator;
    private final BillingMetrics billingMetrics;
    private final Clock clock;

    @Autowired
    public UsageReportService(
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository,
        TenantQuotaRepository tenantQuotaRepository,
        TenantSubscriptionRepository tenantSubscriptionRepository,
        TenantPlanRepository tenantPlanRepository,
        GenerationLogRepository generationLogRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics
    ) {
        this(
            tenantUsageDailyRepository,
            tenantUsageMonthlyRepository,
            tenantQuotaRepository,
            tenantSubscriptionRepository,
            tenantPlanRepository,
            generationLogRepository,
            costCalculator,
            billingMetrics,
            Clock.systemUTC()
        );
    }

    UsageReportService(
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository,
        TenantQuotaRepository tenantQuotaRepository,
        TenantSubscriptionRepository tenantSubscriptionRepository,
        TenantPlanRepository tenantPlanRepository,
        GenerationLogRepository generationLogRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics,
        Clock clock
    ) {
        this.tenantUsageDailyRepository = tenantUsageDailyRepository;
        this.tenantUsageMonthlyRepository = tenantUsageMonthlyRepository;
        this.tenantQuotaRepository = tenantQuotaRepository;
        this.tenantSubscriptionRepository = tenantSubscriptionRepository;
        this.tenantPlanRepository = tenantPlanRepository;
        this.generationLogRepository = generationLogRepository;
        this.costCalculator = costCalculator;
        this.billingMetrics = billingMetrics;
        this.clock = clock;
    }

    public UsageReportPayload getUsageReport(
        String tenantId,
        Instant from,
        Instant to,
        String granularity,
        boolean includeQuota
    ) {
        LocalDate fromDate = (from == null) ? LocalDate.now(clock).minusDays(30) : from.atZone(ZoneOffset.UTC).toLocalDate();
        LocalDate toDate = (to == null) ? LocalDate.now(clock) : to.atZone(ZoneOffset.UTC).toLocalDate();
        YearMonth fromMonth = YearMonth.from(fromDate);
        YearMonth toMonth = YearMonth.from(toDate);

        String normalizedGranularity = (granularity == null) ? "day" : granularity.trim().toLowerCase();
        boolean includeDaily = "day".equals(normalizedGranularity) || "all".equals(normalizedGranularity);
        boolean includeMonthly = "month".equals(normalizedGranularity) || "all".equals(normalizedGranularity);
        if (!includeDaily && !includeMonthly) {
            includeDaily = true;
            includeMonthly = true;
        }

        List<DailyUsageItem> daily = includeDaily
            ? tenantUsageDailyRepository.findByTenantAndDateRange(tenantId, fromDate, toDate).stream()
                .map(entry -> new DailyUsageItem(
                    entry.usageDate(),
                    entry.requestCount(),
                    entry.inputTokens(),
                    entry.outputTokens(),
                    entry.toolCalls(),
                    entry.estimatedCost()
                ))
                .toList()
            : List.of();

        List<MonthlyUsageItem> monthly = includeMonthly
            ? tenantUsageMonthlyRepository.findByTenantAndMonthRange(tenantId, fromMonth, toMonth).stream()
                .map(entry -> new MonthlyUsageItem(
                    entry.usageMonth().toString(),
                    entry.requestCount(),
                    entry.inputTokens(),
                    entry.outputTokens(),
                    entry.toolCalls(),
                    entry.estimatedCost()
                ))
                .toList()
            : List.of();

        BigDecimal estimatedTotal = monthly.stream()
            .map(MonthlyUsageItem::estimatedCost)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        if (estimatedTotal.compareTo(BigDecimal.ZERO) == 0) {
            estimatedTotal = daily.stream().map(DailyUsageItem::estimatedCost).reduce(BigDecimal.ZERO, BigDecimal::add);
        }
        billingMetrics.recordEstimatedCost(estimatedTotal);

        QuotaSnapshot quotaSnapshot = includeQuota ? buildQuotaSnapshot(tenantId) : null;
        return new UsageReportPayload(
            tenantId,
            daily,
            monthly,
            quotaSnapshot,
            estimatedTotal,
            TraceContext.getTraceId()
        );
    }

    private QuotaSnapshot buildQuotaSnapshot(String tenantId) {
        Instant now = Instant.now(clock);
        TenantQuota quota = tenantQuotaRepository.findActive(tenantId, now).orElse(null);
        if (quota == null) {
            return null;
        }

        LocalDate today = LocalDate.now(clock.withZone(ZoneOffset.UTC));
        YearMonth month = YearMonth.now(clock.withZone(ZoneOffset.UTC));
        long usedDailyTokens = generationLogRepository.findByTenantAndDate(tenantId, today).stream()
            .mapToLong(entry -> entry.inputTokens() + entry.outputTokens())
            .sum();
        List<GenerationLogEntry> monthlyLogs = generationLogRepository.findByTenantAndMonth(tenantId, month);
        BigDecimal usedMonthlyCost = costCalculator.sumCost(monthlyLogs);

        boolean dailyBreached = quota.maxDailyTokens() > 0 && usedDailyTokens > quota.maxDailyTokens();
        boolean monthlyBreached = quota.maxMonthlyCost() != null
            && quota.maxMonthlyCost().compareTo(BigDecimal.ZERO) > 0
            && usedMonthlyCost.compareTo(quota.maxMonthlyCost()) > 0;

        TenantSubscription subscription = tenantSubscriptionRepository.findActive(tenantId, now).orElse(null);
        String planCode = subscription == null ? null : subscription.planCode();
        TenantPlan plan = planCode == null ? null : tenantPlanRepository.findByCode(planCode).orElse(null);
        String planName = plan == null ? null : plan.name();

        return new QuotaSnapshot(
            quota.maxQps(),
            quota.maxDailyTokens(),
            quota.maxMonthlyCost(),
            quota.breachAction(),
            usedDailyTokens,
            usedMonthlyCost,
            dailyBreached || monthlyBreached,
            planCode,
            planName
        );
    }

    public record UsageReportPayload(
        String tenantId,
        List<DailyUsageItem> daily,
        List<MonthlyUsageItem> monthly,
        QuotaSnapshot quota,
        BigDecimal estimatedCost,
        String traceId
    ) {
    }

    public record DailyUsageItem(
        LocalDate usageDate,
        long requestCount,
        long inputTokens,
        long outputTokens,
        long toolCalls,
        BigDecimal estimatedCost
    ) {
    }

    public record MonthlyUsageItem(
        String usageMonth,
        long requestCount,
        long inputTokens,
        long outputTokens,
        long toolCalls,
        BigDecimal estimatedCost
    ) {
    }

    public record QuotaSnapshot(
        int maxQps,
        long maxDailyTokens,
        BigDecimal maxMonthlyCost,
        BreachAction breachAction,
        long usedDailyTokens,
        BigDecimal usedMonthlyCost,
        boolean breached,
        String planCode,
        String planName
    ) {
    }
}
