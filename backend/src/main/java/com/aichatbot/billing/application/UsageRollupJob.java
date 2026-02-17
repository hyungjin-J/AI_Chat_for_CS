package com.aichatbot.billing.application;

import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.UUID;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class UsageRollupJob {

    private final UsageRollupService usageRollupService;

    public UsageRollupJob(UsageRollupService usageRollupService) {
        this.usageRollupService = usageRollupService;
    }

    @Scheduled(cron = "${billing.rollup.daily-cron:0 10 0 * * *}", zone = "UTC")
    public void rollupDailyUsage() {
        LocalDate previousDay = LocalDate.now(ZoneOffset.UTC).minusDays(1);
        usageRollupService.rollupDaily(previousDay, UUID.randomUUID().toString());
    }

    @Scheduled(cron = "${billing.rollup.monthly-cron:0 20 0 1 * *}", zone = "UTC")
    public void rollupMonthlyUsage() {
        YearMonth previousMonth = YearMonth.now(ZoneOffset.UTC).minusMonths(1);
        usageRollupService.rollupMonthly(previousMonth, UUID.randomUUID().toString());
    }
}

