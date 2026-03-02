package com.aichatbot.contexts.operations.domain.mapper;

import com.aichatbot.contexts.operations.domain.AdminResourceRow;
import com.aichatbot.contexts.operations.domain.OpsMetricSummaryRow;
import com.aichatbot.contexts.operations.domain.OpsRollbackRow;
import com.aichatbot.contexts.operations.domain.OpsTraceRow;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface BackofficeAdminMapper {

    int insertAdminResource(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("resourceType") String resourceType,
        @Param("resourceKey") String resourceKey,
        @Param("status") String status,
        @Param("payloadJson") String payloadJson,
        @Param("activeFlag") boolean activeFlag,
        @Param("lastRotatedAt") Instant lastRotatedAt,
        @Param("createdBy") UUID createdBy,
        @Param("updatedBy") UUID updatedBy,
        @Param("createdAt") Instant createdAt,
        @Param("updatedAt") Instant updatedAt
    );

    int updateAdminResource(
        @Param("tenantId") UUID tenantId,
        @Param("resourceType") String resourceType,
        @Param("resourceKey") String resourceKey,
        @Param("status") String status,
        @Param("payloadJson") String payloadJson,
        @Param("activeFlag") boolean activeFlag,
        @Param("lastRotatedAt") Instant lastRotatedAt,
        @Param("updatedBy") UUID updatedBy,
        @Param("updatedAt") Instant updatedAt
    );

    AdminResourceRow findAdminResource(
        @Param("tenantId") UUID tenantId,
        @Param("resourceType") String resourceType,
        @Param("resourceKey") String resourceKey
    );

    List<AdminResourceRow> listAdminResources(
        @Param("tenantId") UUID tenantId,
        @Param("resourceType") String resourceType,
        @Param("limit") int limit,
        @Param("offset") int offset
    );

    int deactivateResourcesByType(
        @Param("tenantId") UUID tenantId,
        @Param("resourceType") String resourceType,
        @Param("updatedBy") UUID updatedBy,
        @Param("updatedAt") Instant updatedAt
    );

    List<OpsTraceRow> findOpsTraces(
        @Param("tenantId") UUID tenantId,
        @Param("keyword") String keyword,
        @Param("fromUtc") Instant fromUtc,
        @Param("toUtc") Instant toUtc,
        @Param("limit") int limit,
        @Param("offset") int offset
    );

    List<OpsMetricSummaryRow> findOpsMetricSummary(
        @Param("tenantId") UUID tenantId,
        @Param("fromUtc") Instant fromUtc,
        @Param("toUtc") Instant toUtc
    );

    int insertOpsRollback(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("targetType") String targetType,
        @Param("targetRef") String targetRef,
        @Param("status") String status,
        @Param("reason") String reason,
        @Param("requestedBy") UUID requestedBy,
        @Param("createdAt") Instant createdAt
    );

    List<OpsRollbackRow> findRecentRollbacks(
        @Param("tenantId") UUID tenantId,
        @Param("limit") int limit
    );
}
