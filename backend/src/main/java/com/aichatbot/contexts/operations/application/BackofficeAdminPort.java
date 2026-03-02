package com.aichatbot.contexts.operations.application;

import com.aichatbot.contexts.operations.domain.AdminResourceRow;
import com.aichatbot.contexts.operations.domain.OpsMetricSummaryRow;
import com.aichatbot.contexts.operations.domain.OpsRollbackRow;
import com.aichatbot.contexts.operations.domain.OpsTraceRow;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface BackofficeAdminPort {

    AdminResourceRow upsertResource(
        UUID tenantId,
        String resourceType,
        String resourceKey,
        String status,
        String payloadJson,
        boolean activeFlag,
        Instant lastRotatedAt,
        UUID actorUserId,
        Instant nowUtc
    );

    Optional<AdminResourceRow> findResource(UUID tenantId, String resourceType, String resourceKey);

    List<AdminResourceRow> listResources(UUID tenantId, String resourceType, int limit, int offset);

    void deactivateResourcesByType(UUID tenantId, String resourceType, UUID actorUserId, Instant nowUtc);

    List<OpsTraceRow> findOpsTraces(
        UUID tenantId,
        String keyword,
        Instant fromUtc,
        Instant toUtc,
        int limit,
        int offset
    );

    List<OpsMetricSummaryRow> findOpsMetricSummary(UUID tenantId, Instant fromUtc, Instant toUtc);

    UUID createRollback(
        UUID tenantId,
        String targetType,
        String targetRef,
        String reason,
        UUID requestedBy,
        Instant nowUtc
    );

    List<OpsRollbackRow> findRecentRollbacks(UUID tenantId, int limit);
}
