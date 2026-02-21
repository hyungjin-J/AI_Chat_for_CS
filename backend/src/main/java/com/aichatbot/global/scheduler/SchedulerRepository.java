package com.aichatbot.global.scheduler;

import com.aichatbot.global.scheduler.domain.RetentionPolicyRecord;
import com.aichatbot.global.scheduler.domain.SchedulerLockRecord;
import com.aichatbot.global.scheduler.domain.mapper.SchedulerMapper;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Repository
public class SchedulerRepository {

    private final SchedulerMapper schedulerMapper;

    public SchedulerRepository(SchedulerMapper schedulerMapper) {
        this.schedulerMapper = schedulerMapper;
    }

    public boolean tryAcquireLock(String lockKey, UUID ownerId, Instant nowUtc, Instant leaseUntilUtc) {
        int updated = schedulerMapper.updateLockLease(lockKey, ownerId, nowUtc, leaseUntilUtc, nowUtc);
        if (updated > 0) {
            return true;
        }
        try {
            return schedulerMapper.insertLock(lockKey, ownerId, leaseUntilUtc, nowUtc) == 1;
        } catch (DuplicateKeyException duplicateKeyException) {
            return schedulerMapper.updateLockLease(lockKey, ownerId, nowUtc, leaseUntilUtc, nowUtc) > 0;
        }
    }

    public boolean heartbeatLock(String lockKey, UUID ownerId, Instant leaseUntilUtc, Instant heartbeatAt) {
        return schedulerMapper.heartbeatLock(lockKey, ownerId, leaseUntilUtc, heartbeatAt) == 1;
    }

    public boolean forceRecoverStaleLock(String lockKey, UUID newOwnerId, Instant newLeaseUntilUtc, Instant nowUtc) {
        return schedulerMapper.forceRecoverStaleLock(lockKey, newOwnerId, newLeaseUntilUtc, nowUtc) == 1;
    }

    public List<SchedulerLockRecord> findStaleLocks(Instant nowUtc, Instant staleBeforeUtc, int limit) {
        return schedulerMapper.findStaleLocks(nowUtc, staleBeforeUtc, limit);
    }

    public List<RetentionPolicyRecord> listRetentionPolicies() {
        return schedulerMapper.listRetentionPolicies();
    }

    public long deleteBefore(String tableName, Instant cutoff) {
        if ("tb_ops_event".equals(tableName)) {
            return schedulerMapper.deleteOpsEventBefore(cutoff);
        }
        if ("tb_audit_log".equals(tableName)) {
            return schedulerMapper.deleteAuditLogBefore(cutoff);
        }
        if ("tb_api_metric_hourly".equals(tableName)) {
            return schedulerMapper.deleteApiMetricHourlyBefore(cutoff);
        }
        return 0L;
    }

    public UUID createRetentionRun(String tableName, Instant startedAt, UUID traceId) {
        UUID runId = UUID.randomUUID();
        schedulerMapper.insertRetentionRun(runId, tableName, startedAt, "RUNNING", traceId);
        return runId;
    }

    public void completeRetentionRun(UUID runId, Instant endedAt, long deletedRows, String status) {
        schedulerMapper.updateRetentionRun(runId, endedAt, deletedRows, status);
    }

    public void upsertPartitionPlan(String tableName, LocalDate bucketMonthUtc, String status, Instant updatedAt) {
        int updated = schedulerMapper.upsertPartitionPlan(tableName, bucketMonthUtc, status, updatedAt);
        if (updated > 0) {
            return;
        }
        try {
            schedulerMapper.insertPartitionPlan(tableName, bucketMonthUtc, status, updatedAt);
        } catch (DuplicateKeyException duplicateKeyException) {
            schedulerMapper.upsertPartitionPlan(tableName, bucketMonthUtc, status, updatedAt);
        }
    }
}
