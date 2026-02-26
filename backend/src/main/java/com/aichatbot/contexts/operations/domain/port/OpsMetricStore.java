package com.aichatbot.contexts.operations.domain.port;

import com.aichatbot.contexts.operations.domain.OpsEventAggregate;
import com.aichatbot.contexts.operations.domain.OpsMetricRow;
import com.aichatbot.contexts.operations.domain.OpsMetricTotal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public interface OpsMetricStore {

    List<OpsEventAggregate> aggregateHourly(Instant fromUtc, Instant toUtc, List<String> metricKeys);

    void upsertHourlyMetric(UUID tenantId, Instant hourBucketUtc, String metricKey, long metricValue, Instant updatedAt);

    List<OpsMetricRow> findSeries(UUID tenantId, Instant fromUtc, Instant toUtc);

    List<OpsMetricTotal> findSummary(UUID tenantId, Instant fromUtc, Instant toUtc);
}
