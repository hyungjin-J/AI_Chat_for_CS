package com.aichatbot.ops.infrastructure;

import com.aichatbot.ops.domain.OpsBlockRecord;
import com.aichatbot.ops.domain.OpsEventAggregate;
import com.aichatbot.ops.domain.OpsMetricRow;
import com.aichatbot.ops.domain.OpsMetricTotal;
import com.aichatbot.ops.domain.mapper.OpsMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Repository
public class OpsRepository {

    private final OpsMapper opsMapper;

    public OpsRepository(OpsMapper opsMapper) {
        this.opsMapper = opsMapper;
    }

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

    public List<OpsEventAggregate> aggregateHourly(Instant fromUtc, Instant toUtc, List<String> metricKeys) {
        return opsMapper.aggregateHourly(fromUtc, toUtc, metricKeys);
    }

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

    public List<OpsMetricRow> findSeries(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsMapper.findSeries(tenantId, fromUtc, toUtc);
    }

    public List<OpsMetricTotal> findSummary(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsMapper.findSummary(tenantId, fromUtc, toUtc);
    }

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

    public Optional<OpsBlockRecord> findActiveBlock(UUID tenantId, String blockType, String blockValue, Instant nowUtc) {
        return Optional.ofNullable(opsMapper.findActiveBlock(tenantId, blockType, blockValue, nowUtc));
    }
}

