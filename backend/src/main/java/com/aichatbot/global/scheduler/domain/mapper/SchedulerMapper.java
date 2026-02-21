package com.aichatbot.global.scheduler.domain.mapper;

import com.aichatbot.global.scheduler.domain.RetentionPolicyRecord;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface SchedulerMapper {

    int updateLockLease(@Param("lockKey") String lockKey,
                        @Param("ownerId") UUID ownerId,
                        @Param("nowUtc") Instant nowUtc,
                        @Param("leaseUntilUtc") Instant leaseUntilUtc,
                        @Param("updatedAt") Instant updatedAt);

    int insertLock(@Param("lockKey") String lockKey,
                   @Param("ownerId") UUID ownerId,
                   @Param("leaseUntilUtc") Instant leaseUntilUtc,
                   @Param("updatedAt") Instant updatedAt);

    List<RetentionPolicyRecord> listRetentionPolicies();

    int deleteOpsEventBefore(@Param("cutoff") Instant cutoff);

    int deleteAuditLogBefore(@Param("cutoff") Instant cutoff);

    int deleteApiMetricHourlyBefore(@Param("cutoff") Instant cutoff);

    int insertRetentionRun(@Param("id") UUID id,
                           @Param("tableName") String tableName,
                           @Param("startedAt") Instant startedAt,
                           @Param("status") String status,
                           @Param("traceId") UUID traceId);

    int updateRetentionRun(@Param("id") UUID id,
                           @Param("endedAt") Instant endedAt,
                           @Param("deletedRows") long deletedRows,
                           @Param("status") String status);

    int upsertPartitionPlan(@Param("tableName") String tableName,
                            @Param("bucketMonthUtc") LocalDate bucketMonthUtc,
                            @Param("status") String status,
                            @Param("updatedAt") Instant updatedAt);

    int insertPartitionPlan(@Param("tableName") String tableName,
                            @Param("bucketMonthUtc") LocalDate bucketMonthUtc,
                            @Param("status") String status,
                            @Param("updatedAt") Instant updatedAt);
}
