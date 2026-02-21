package com.aichatbot.global.scheduler;

import com.aichatbot.global.scheduler.domain.SchedulerLockRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SchedulerLockJanitorJobTest {

    @Test
    void shouldAttemptRecoveryForEachStaleLock() {
        SchedulerLockService lockService = mock(SchedulerLockService.class);
        SchedulerLockJanitorJob job = new SchedulerLockJanitorJob(lockService);

        SchedulerLockRecord first = new SchedulerLockRecord(
            "ops_metric_hourly_aggregation",
            UUID.randomUUID(),
            Instant.parse("2026-03-10T00:00:00Z"),
            10L,
            Instant.parse("2026-03-10T00:00:00Z"),
            Instant.parse("2026-03-09T23:55:00Z"),
            null,
            1L
        );
        SchedulerLockRecord second = new SchedulerLockRecord(
            "data_retention_daily",
            UUID.randomUUID(),
            Instant.parse("2026-03-10T00:00:00Z"),
            12L,
            Instant.parse("2026-03-10T00:00:00Z"),
            Instant.parse("2026-03-09T23:50:00Z"),
            null,
            2L
        );

        when(lockService.findStaleLocks(any(), eq(200))).thenReturn(List.of(first, second));
        when(lockService.forceRecoverStaleLock(eq(first.lockKey()), any())).thenReturn(true);
        when(lockService.forceRecoverStaleLock(eq(second.lockKey()), any())).thenReturn(false);

        job.recoverStaleLocks();

        verify(lockService).forceRecoverStaleLock(eq(first.lockKey()), any());
        verify(lockService).emitLockEvent(eq(first.lockKey()), eq("self_healing_recovered"));
        verify(lockService).forceRecoverStaleLock(eq(second.lockKey()), any());
        verify(lockService).emitLockEvent(eq(second.lockKey()), eq("self_healing_failed"));
    }
}
