package com.aichatbot.contexts.billing.infrastructure;

import com.aichatbot.contexts.billing.application.UsageRollupService;
import com.aichatbot.contexts.billing.domain.model.CostRateCard;
import com.aichatbot.contexts.billing.domain.model.GenerationLogEntry;
import com.aichatbot.contexts.billing.domain.model.TenantDailyUsage;
import com.aichatbot.contexts.billing.domain.model.TenantMonthlyUsage;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;

final class BillingParityScenarioRunner {

    private BillingParityScenarioRunner() {
    }

    static Snapshot run(
        GenerationLogRepository generationLogRepository,
        RateCardRepository rateCardRepository,
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository,
        UsageRollupService usageRollupService
    ) {
        clear(
            generationLogRepository,
            rateCardRepository,
            tenantUsageDailyRepository,
            tenantUsageMonthlyRepository
        );

        rateCardRepository.save(new CostRateCard(
            "rate-parity-1",
            "provider-default",
            "model-default",
            new BigDecimal("0.001"),
            new BigDecimal("0.002"),
            new BigDecimal("0.010"),
            Instant.parse("2026-01-01T00:00:00Z"),
            null
        ));

        generationLogRepository.save(new GenerationLogEntry(
            "parity-g1",
            "tenant-a",
            "msg-1",
            "provider-default",
            "model-default",
            1000,
            500,
            1,
            "masked",
            "trace-parity-1",
            Instant.parse("2026-02-17T05:00:00Z")
        ));
        generationLogRepository.save(new GenerationLogEntry(
            "parity-g2",
            "tenant-a",
            "msg-2",
            "provider-default",
            "model-default",
            2000,
            1000,
            2,
            "masked",
            "trace-parity-2",
            Instant.parse("2026-02-17T06:00:00Z")
        ));
        generationLogRepository.save(new GenerationLogEntry(
            "parity-g3",
            "tenant-a",
            "msg-3",
            "provider-default",
            "model-default",
            500,
            500,
            0,
            "masked",
            "trace-parity-3",
            Instant.parse("2026-02-18T08:30:00Z")
        ));

        LocalDate day1 = LocalDate.of(2026, 2, 17);
        LocalDate day2 = LocalDate.of(2026, 2, 18);
        YearMonth month = YearMonth.of(2026, 2);
        usageRollupService.rollupDaily(day1, "trace-rollup-day1");
        usageRollupService.rollupDaily(day2, "trace-rollup-day2");
        usageRollupService.rollupMonthly(month, "trace-rollup-month");

        TenantDailyUsage day1Usage = tenantUsageDailyRepository.findOne("tenant-a", day1);
        TenantDailyUsage day2Usage = tenantUsageDailyRepository.findOne("tenant-a", day2);
        TenantMonthlyUsage monthUsage = tenantUsageMonthlyRepository.findOne("tenant-a", month);

        return new Snapshot(
            normalize(day1Usage.requestCount()),
            normalize(day1Usage.inputTokens()),
            normalize(day1Usage.outputTokens()),
            normalize(day1Usage.toolCalls()),
            day1Usage.estimatedCost().setScale(6).toPlainString(),
            normalize(day2Usage.requestCount()),
            normalize(day2Usage.inputTokens()),
            normalize(day2Usage.outputTokens()),
            normalize(day2Usage.toolCalls()),
            day2Usage.estimatedCost().setScale(6).toPlainString(),
            normalize(monthUsage.requestCount()),
            normalize(monthUsage.inputTokens()),
            normalize(monthUsage.outputTokens()),
            normalize(monthUsage.toolCalls()),
            monthUsage.estimatedCost().setScale(6).toPlainString()
        );
    }

    static Snapshot expected() {
        return new Snapshot(
            2L,
            3000L,
            1500L,
            3L,
            "0.036000",
            1L,
            500L,
            500L,
            0L,
            "0.001500",
            3L,
            3500L,
            2000L,
            3L,
            "0.037500"
        );
    }

    static void clear(
        GenerationLogRepository generationLogRepository,
        RateCardRepository rateCardRepository,
        TenantUsageDailyRepository tenantUsageDailyRepository,
        TenantUsageMonthlyRepository tenantUsageMonthlyRepository
    ) {
        tenantUsageMonthlyRepository.clear();
        tenantUsageDailyRepository.clear();
        generationLogRepository.clear();
        rateCardRepository.clear();
    }

    private static long normalize(long value) {
        return value;
    }

    record Snapshot(
        long day1RequestCount,
        long day1InputTokens,
        long day1OutputTokens,
        long day1ToolCalls,
        String day1EstimatedCost,
        long day2RequestCount,
        long day2InputTokens,
        long day2OutputTokens,
        long day2ToolCalls,
        String day2EstimatedCost,
        long monthRequestCount,
        long monthInputTokens,
        long monthOutputTokens,
        long monthToolCalls,
        String monthEstimatedCost
    ) {
    }
}
