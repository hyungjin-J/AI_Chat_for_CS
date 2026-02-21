package com.aichatbot.global.scheduler;

import com.aichatbot.global.observability.TraceIdNormalizer;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class DataRetentionJob {

    private final SchedulerLockService schedulerLockService;
    private final SchedulerRepository schedulerRepository;
    private final Clock clock;

    @Autowired
    public DataRetentionJob(SchedulerLockService schedulerLockService, SchedulerRepository schedulerRepository) {
        this(schedulerLockService, schedulerRepository, Clock.systemUTC());
    }

    DataRetentionJob(SchedulerLockService schedulerLockService, SchedulerRepository schedulerRepository, Clock clock) {
        this.schedulerLockService = schedulerLockService;
        this.schedulerRepository = schedulerRepository;
        this.clock = clock;
    }

    @Scheduled(cron = "${data.retention.daily-cron:0 45 0 * * *}", zone = "UTC")
    public void runRetention() {
        if (!schedulerLockService.tryAcquire("data_retention_daily", java.time.Duration.ofMinutes(5))) {
            return;
        }
        Instant now = Instant.now(clock);
        UUID traceId = TraceIdNormalizer.toUuid(UUID.randomUUID().toString());
        schedulerRepository.listRetentionPolicies().stream()
            .filter(policy -> policy.enabled() && policy.retentionDays() > 0)
            .forEach(policy -> {
                UUID runId = schedulerRepository.createRetentionRun(policy.tableName(), now, traceId);
                Instant cutoff = now.minus(policy.retentionDays(), ChronoUnit.DAYS);
                long deletedRows = schedulerRepository.deleteBefore(policy.tableName(), cutoff);
                schedulerRepository.completeRetentionRun(runId, Instant.now(clock), deletedRows, "DONE");
            });
    }
}
