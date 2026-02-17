package com.aichatbot.billing.application;

import com.aichatbot.billing.domain.model.BreachAction;
import com.aichatbot.billing.domain.model.GenerationLogEntry;
import com.aichatbot.billing.domain.model.TenantQuota;
import com.aichatbot.billing.domain.service.CostCalculator;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.billing.infrastructure.TenantQuotaRepository;
import com.aichatbot.global.error.QuotaExceededException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class BudgetEnforcementService {

    private static final long DEFAULT_RETRY_AFTER_SECONDS = 30L;

    private final TenantQuotaRepository tenantQuotaRepository;
    private final GenerationLogRepository generationLogRepository;
    private final CostCalculator costCalculator;
    private final BillingMetrics billingMetrics;
    private final Clock clock;

    @Autowired
    public BudgetEnforcementService(
        TenantQuotaRepository tenantQuotaRepository,
        GenerationLogRepository generationLogRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics
    ) {
        this(
            tenantQuotaRepository,
            generationLogRepository,
            costCalculator,
            billingMetrics,
            Clock.systemUTC()
        );
    }

    BudgetEnforcementService(
        TenantQuotaRepository tenantQuotaRepository,
        GenerationLogRepository generationLogRepository,
        CostCalculator costCalculator,
        BillingMetrics billingMetrics,
        Clock clock
    ) {
        this.tenantQuotaRepository = tenantQuotaRepository;
        this.generationLogRepository = generationLogRepository;
        this.costCalculator = costCalculator;
        this.billingMetrics = billingMetrics;
        this.clock = clock;
    }

    public void enforceGenerationBudget(
        String tenantId,
        String providerId,
        String modelId,
        int inputTokens,
        int outputTokens,
        int toolCalls
    ) {
        Instant now = Instant.now(clock);
        Optional<TenantQuota> activeQuota = tenantQuotaRepository.findActive(tenantId, now);
        if (activeQuota.isEmpty()) {
            return;
        }

        TenantQuota quota = activeQuota.get();
        enforceDailyTokenLimit(tenantId, quota, inputTokens, outputTokens);
        enforceMonthlyCostLimit(tenantId, providerId, modelId, quota, now, inputTokens, outputTokens, toolCalls);
    }

    private void enforceDailyTokenLimit(String tenantId, TenantQuota quota, int inputTokens, int outputTokens) {
        if (quota.maxDailyTokens() <= 0) {
            return;
        }

        LocalDate today = LocalDate.now(clock.withZone(ZoneOffset.UTC));
        long usedTokens = generationLogRepository.findByTenantAndDate(tenantId, today).stream()
            .mapToLong(entry -> entry.inputTokens() + entry.outputTokens())
            .sum();
        long projectedTokens = usedTokens + inputTokens + outputTokens;

        if (projectedTokens > quota.maxDailyTokens()) {
            billingMetrics.incrementQuotaBreach();
            billingMetrics.incrementTokenBudgetExceeded();
            throw new QuotaExceededException(
                toStatus(quota.breachAction()),
                toErrorCode(quota.breachAction()),
                "Daily token budget exceeded",
                quota.maxDailyTokens(),
                Math.max(0L, quota.maxDailyTokens() - usedTokens),
                today.plusDays(1).atStartOfDay(ZoneOffset.UTC).toEpochSecond(),
                DEFAULT_RETRY_AFTER_SECONDS
            );
        }
    }

    private void enforceMonthlyCostLimit(
        String tenantId,
        String providerId,
        String modelId,
        TenantQuota quota,
        Instant now,
        int inputTokens,
        int outputTokens,
        int toolCalls
    ) {
        if (quota.maxMonthlyCost() == null || quota.maxMonthlyCost().compareTo(BigDecimal.ZERO) <= 0) {
            return;
        }

        YearMonth month = YearMonth.from(now.atZone(ZoneOffset.UTC));
        List<GenerationLogEntry> monthEntries = generationLogRepository.findByTenantAndMonth(tenantId, month);
        BigDecimal existingCost = costCalculator.sumCost(monthEntries);
        BigDecimal projectedCost = existingCost.add(
            costCalculator.estimateCostForProjectedRequest(providerId, modelId, now, inputTokens, outputTokens, toolCalls)
        );
        billingMetrics.recordEstimatedCost(projectedCost);

        if (projectedCost.compareTo(quota.maxMonthlyCost()) > 0) {
            billingMetrics.incrementQuotaBreach();
            long limitCents = toCents(quota.maxMonthlyCost());
            long usedCents = toCents(existingCost);
            throw new QuotaExceededException(
                toStatus(quota.breachAction()),
                toErrorCode(quota.breachAction()),
                "Monthly cost budget exceeded",
                limitCents,
                Math.max(0L, limitCents - usedCents),
                month.plusMonths(1).atDay(1).atStartOfDay(ZoneOffset.UTC).toEpochSecond(),
                DEFAULT_RETRY_AFTER_SECONDS
            );
        }
    }

    private long toCents(BigDecimal amount) {
        return amount.multiply(BigDecimal.valueOf(100L)).setScale(0, RoundingMode.HALF_UP).longValue();
    }

    private HttpStatus toStatus(BreachAction action) {
        if (action == BreachAction.BLOCK_403) {
            return HttpStatus.FORBIDDEN;
        }
        return HttpStatus.TOO_MANY_REQUESTS;
    }

    private String toErrorCode(BreachAction action) {
        if (action == BreachAction.BLOCK_403) {
            return "API-008-403-BUDGET";
        }
        return "API-008-429-BUDGET";
    }
}
