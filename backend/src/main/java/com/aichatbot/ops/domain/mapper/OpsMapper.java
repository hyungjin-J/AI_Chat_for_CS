package com.aichatbot.ops.domain.mapper;

import com.aichatbot.ops.domain.OpsBlockRecord;
import com.aichatbot.ops.domain.OpsEventAggregate;
import com.aichatbot.ops.domain.OpsMetricRow;
import com.aichatbot.ops.domain.OpsMetricTotal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface OpsMapper {

    int insertOpsEvent(@Param("id") UUID id,
                       @Param("tenantId") UUID tenantId,
                       @Param("traceId") UUID traceId,
                       @Param("eventTime") Instant eventTime,
                       @Param("eventType") String eventType,
                       @Param("metricKey") String metricKey,
                       @Param("metricValue") long metricValue,
                       @Param("dimensionsJson") String dimensionsJson);

    List<OpsEventAggregate> aggregateHourly(@Param("fromUtc") Instant fromUtc,
                                            @Param("toUtc") Instant toUtc,
                                            @Param("metricKeys") List<String> metricKeys);

    int updateHourlyMetric(@Param("tenantId") UUID tenantId,
                           @Param("hourBucketUtc") Instant hourBucketUtc,
                           @Param("metricKey") String metricKey,
                           @Param("metricValue") long metricValue,
                           @Param("updatedAt") Instant updatedAt);

    int insertHourlyMetric(@Param("id") UUID id,
                           @Param("tenantId") UUID tenantId,
                           @Param("hourBucketUtc") Instant hourBucketUtc,
                           @Param("metricKey") String metricKey,
                           @Param("metricValue") long metricValue,
                           @Param("updatedAt") Instant updatedAt);

    List<OpsMetricRow> findSeries(@Param("tenantId") UUID tenantId,
                                  @Param("fromUtc") Instant fromUtc,
                                  @Param("toUtc") Instant toUtc);

    List<OpsMetricTotal> findSummary(@Param("tenantId") UUID tenantId,
                                     @Param("fromUtc") Instant fromUtc,
                                     @Param("toUtc") Instant toUtc);

    int updateExistingBlock(@Param("tenantId") UUID tenantId,
                            @Param("blockType") String blockType,
                            @Param("blockValue") String blockValue,
                            @Param("status") String status,
                            @Param("reason") String reason,
                            @Param("expiresAt") Instant expiresAt,
                            @Param("updatedAt") Instant updatedAt);

    int insertBlock(@Param("id") UUID id,
                    @Param("tenantId") UUID tenantId,
                    @Param("blockType") String blockType,
                    @Param("blockValue") String blockValue,
                    @Param("status") String status,
                    @Param("reason") String reason,
                    @Param("expiresAt") Instant expiresAt,
                    @Param("createdBy") UUID createdBy,
                    @Param("updatedAt") Instant updatedAt);

    OpsBlockRecord findActiveBlock(@Param("tenantId") UUID tenantId,
                                   @Param("blockType") String blockType,
                                   @Param("blockValue") String blockValue,
                                   @Param("nowUtc") Instant nowUtc);
}
