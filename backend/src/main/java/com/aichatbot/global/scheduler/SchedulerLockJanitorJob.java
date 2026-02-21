package com.aichatbot.global.scheduler;

import com.aichatbot.global.scheduler.domain.SchedulerLockRecord;
import java.time.Duration;
import java.util.List;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class SchedulerLockJanitorJob {

    private final SchedulerLockService schedulerLockService;

    public SchedulerLockJanitorJob(SchedulerLockService schedulerLockService) {
        this.schedulerLockService = schedulerLockService;
    }

    @Scheduled(cron = "${scheduler.lock.janitor-cron:30 * * * * *}", zone = "UTC")
    public void recoverStaleLocks() {
        List<SchedulerLockRecord> staleLocks = schedulerLockService.findStaleLocks(Duration.ofMinutes(5), 200);
        for (SchedulerLockRecord staleLock : staleLocks) {
            boolean recovered = schedulerLockService.forceRecoverStaleLock(staleLock.lockKey(), Duration.ofMinutes(2));
            schedulerLockService.emitLockEvent(
                staleLock.lockKey(),
                recovered ? "self_healing_recovered" : "self_healing_failed"
            );
        }
    }
}
