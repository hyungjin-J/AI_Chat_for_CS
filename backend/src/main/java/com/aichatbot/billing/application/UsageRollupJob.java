package com.aichatbot.billing.application;

import com.aichatbot.global.scheduler.SchedulerLockService;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.UUID;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class UsageRollupJob {

    private final UsageRollupService usageRollupService;
    private final SchedulerLockService schedulerLockService;

    public UsageRollupJob(UsageRollupService usageRollupService, SchedulerLockService schedulerLockService) {
        this.usageRollupService = usageRollupService;
        this.schedulerLockService = schedulerLockService;
    }

    @Scheduled(cron = "${billing.rollup.daily-cron:0 10 0 * * *}", zone = "UTC")
    public void rollupDailyUsage() {
        if (!schedulerLockService.tryAcquire("billing_rollup_daily", java.time.Duration.ofMinutes(5))) {
            return;
        }
        LocalDate previousDay = LocalDate.now(ZoneOffset.UTC).minusDays(1);
        usageRollupService.rollupDaily(previousDay, UUID.randomUUID().toString());
    }

    @Scheduled(cron = "${billing.rollup.monthly-cron:0 20 0 1 * *}", zone = "UTC")
    public void rollupMonthlyUsage() {
        if (!schedulerLockService.tryAcquire("billing_rollup_monthly", java.time.Duration.ofMinutes(10))) {
            return;
        }
        YearMonth previousMonth = YearMonth.now(ZoneOffset.UTC).minusMonths(1);
        usageRollupService.rollupMonthly(previousMonth, UUID.randomUUID().toString());
    }
}
