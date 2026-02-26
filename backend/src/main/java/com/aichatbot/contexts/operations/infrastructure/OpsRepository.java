package com.aichatbot.contexts.operations.infrastructure;

import com.aichatbot.contexts.operations.domain.OpsBlockRecord;
import com.aichatbot.contexts.operations.domain.OpsEventAggregate;
import com.aichatbot.contexts.operations.domain.OpsMetricRow;
import com.aichatbot.contexts.operations.domain.OpsMetricTotal;
import com.aichatbot.contexts.operations.domain.mapper.OpsMapper;
import com.aichatbot.contexts.operations.domain.port.OpsBlockStore;
import com.aichatbot.contexts.operations.domain.port.OpsEventStore;
import com.aichatbot.contexts.operations.domain.port.OpsMetricStore;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Primary;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Primary
@Repository
public class OpsRepository implements OpsEventStore, OpsMetricStore, OpsBlockStore {

    private final OpsMapper opsMapper;

    public OpsRepository(OpsMapper opsMapper) {
        this.opsMapper = opsMapper;
    }

    @Override
    public void insertOpsEvent(
        UUID id,
        UUID tenantId,
        UUID traceId,
        Instant eventTime,
        String eventType,
        String metricKey,
        long metricValue,
        String dimensionsJson
    ) {
        opsMapper.insertOpsEvent(id, tenantId, traceId, eventTime, eventType, metricKey, metricValue, dimensionsJson);
    }

    @Override
    public List<OpsEventAggregate> aggregateHourly(Instant fromUtc, Instant toUtc, List<String> metricKeys) {
        return opsMapper.aggregateHourly(fromUtc, toUtc, metricKeys);
    }

    @Override
    public void upsertHourlyMetric(UUID tenantId, Instant hourBucketUtc, String metricKey, long metricValue, Instant updatedAt) {
        int updated = opsMapper.updateHourlyMetric(tenantId, hourBucketUtc, metricKey, metricValue, updatedAt);
        if (updated > 0) {
            return;
        }

        try {
            opsMapper.insertHourlyMetric(UUID.randomUUID(), tenantId, hourBucketUtc, metricKey, metricValue, updatedAt);
        } catch (DuplicateKeyException duplicateKeyException) {
            opsMapper.updateHourlyMetric(tenantId, hourBucketUtc, metricKey, metricValue, updatedAt);
        }
    }

    @Override
    public List<OpsMetricRow> findSeries(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsMapper.findSeries(tenantId, fromUtc, toUtc);
    }

    @Override
    public List<OpsMetricTotal> findSummary(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsMapper.findSummary(tenantId, fromUtc, toUtc);
    }

    @Override
    public void upsertBlock(
        UUID tenantId,
        String blockType,
        String blockValue,
        String status,
        String reason,
        Instant expiresAt,
        UUID createdBy,
        Instant updatedAt
    ) {
        int updated = opsMapper.updateExistingBlock(tenantId, blockType, blockValue, status, reason, expiresAt, updatedAt);
        if (updated > 0) {
            return;
        }

        try {
            opsMapper.insertBlock(UUID.randomUUID(), tenantId, blockType, blockValue, status, reason, expiresAt, createdBy, updatedAt);
        } catch (DuplicateKeyException duplicateKeyException) {
            opsMapper.updateExistingBlock(tenantId, blockType, blockValue, status, reason, expiresAt, updatedAt);
        }
    }

    @Override
    public Optional<OpsBlockRecord> findActiveBlock(UUID tenantId, String blockType, String blockValue, Instant nowUtc) {
        return Optional.ofNullable(opsMapper.findActiveBlock(tenantId, blockType, blockValue, nowUtc));
    }
}


