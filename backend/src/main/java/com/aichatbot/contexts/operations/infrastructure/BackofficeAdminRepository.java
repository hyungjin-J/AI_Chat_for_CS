package com.aichatbot.contexts.operations.infrastructure;

import com.aichatbot.contexts.operations.application.BackofficeAdminPort;
import com.aichatbot.contexts.operations.domain.AdminResourceRow;
import com.aichatbot.contexts.operations.domain.OpsMetricSummaryRow;
import com.aichatbot.contexts.operations.domain.OpsRollbackRow;
import com.aichatbot.contexts.operations.domain.OpsTraceRow;
import com.aichatbot.contexts.operations.domain.mapper.BackofficeAdminMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Primary;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Primary
@Repository
public class BackofficeAdminRepository implements BackofficeAdminPort {

    private final BackofficeAdminMapper mapper;

    public BackofficeAdminRepository(BackofficeAdminMapper mapper) {
        this.mapper = mapper;
    }

    public AdminResourceRow upsertResource(
        UUID tenantId,
        String resourceType,
        String resourceKey,
        String status,
        String payloadJson,
        boolean activeFlag,
        Instant lastRotatedAt,
        UUID actorUserId,
        Instant nowUtc
    ) {
        int updated = mapper.updateAdminResource(
            tenantId,
            resourceType,
            resourceKey,
            status,
            payloadJson,
            activeFlag,
            lastRotatedAt,
            actorUserId,
            nowUtc
        );
        if (updated == 0) {
            try {
                mapper.insertAdminResource(
                    UUID.randomUUID(),
                    tenantId,
                    resourceType,
                    resourceKey,
                    status,
                    payloadJson,
                    activeFlag,
                    lastRotatedAt,
                    actorUserId,
                    actorUserId,
                    nowUtc,
                    nowUtc
                );
            } catch (DuplicateKeyException duplicateKeyException) {
                mapper.updateAdminResource(
                    tenantId,
                    resourceType,
                    resourceKey,
                    status,
                    payloadJson,
                    activeFlag,
                    lastRotatedAt,
                    actorUserId,
                    nowUtc
                );
            }
        }
        return mapper.findAdminResource(tenantId, resourceType, resourceKey);
    }

    public Optional<AdminResourceRow> findResource(UUID tenantId, String resourceType, String resourceKey) {
        return Optional.ofNullable(mapper.findAdminResource(tenantId, resourceType, resourceKey));
    }

    public List<AdminResourceRow> listResources(UUID tenantId, String resourceType, int limit, int offset) {
        return mapper.listAdminResources(tenantId, resourceType, limit, offset);
    }

    public void deactivateResourcesByType(UUID tenantId, String resourceType, UUID actorUserId, Instant nowUtc) {
        mapper.deactivateResourcesByType(tenantId, resourceType, actorUserId, nowUtc);
    }

    public List<OpsTraceRow> findOpsTraces(
        UUID tenantId,
        String keyword,
        Instant fromUtc,
        Instant toUtc,
        int limit,
        int offset
    ) {
        return mapper.findOpsTraces(tenantId, keyword, fromUtc, toUtc, limit, offset);
    }

    public List<OpsMetricSummaryRow> findOpsMetricSummary(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return mapper.findOpsMetricSummary(tenantId, fromUtc, toUtc);
    }

    public UUID createRollback(
        UUID tenantId,
        String targetType,
        String targetRef,
        String reason,
        UUID requestedBy,
        Instant nowUtc
    ) {
        UUID rollbackId = UUID.randomUUID();
        mapper.insertOpsRollback(
            rollbackId,
            tenantId,
            targetType,
            targetRef,
            "REQUESTED",
            reason,
            requestedBy,
            nowUtc
        );
        return rollbackId;
    }

    public List<OpsRollbackRow> findRecentRollbacks(UUID tenantId, int limit) {
        return mapper.findRecentRollbacks(tenantId, limit);
    }
}
