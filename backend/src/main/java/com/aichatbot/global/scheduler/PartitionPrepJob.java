package com.aichatbot.global.scheduler;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class PartitionPrepJob {

    private static final List<String> TABLES = List.of("tb_ops_event", "tb_audit_log", "tb_api_metric_hourly");

    private final SchedulerLockService schedulerLockService;
    private final SchedulerRepository schedulerRepository;
    private final Clock clock;

    @Autowired
    public PartitionPrepJob(SchedulerLockService schedulerLockService, SchedulerRepository schedulerRepository) {
        this(schedulerLockService, schedulerRepository, Clock.systemUTC());
    }

    PartitionPrepJob(SchedulerLockService schedulerLockService, SchedulerRepository schedulerRepository, Clock clock) {
        this.schedulerLockService = schedulerLockService;
        this.schedulerRepository = schedulerRepository;
        this.clock = clock;
    }

    @Scheduled(cron = "${partition.prep.daily-cron:0 55 0 * * *}", zone = "UTC")
    public void prepareNextMonthPartitions() {
        if (!schedulerLockService.tryAcquire("partition_prep_daily", java.time.Duration.ofMinutes(5))) {
            return;
        }
        LocalDate nextMonthBucket = LocalDate.now(clock.withZone(ZoneOffset.UTC))
            .withDayOfMonth(1)
            .plusMonths(1);
        Instant now = Instant.now(clock);
        for (String tableName : TABLES) {
            schedulerRepository.upsertPartitionPlan(tableName, nextMonthBucket, "PLANNED", now);
        }
    }
}
