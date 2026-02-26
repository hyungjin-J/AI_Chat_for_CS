package com.aichatbot.contexts.operations.application;

import com.aichatbot.contexts.operations.domain.port.OpsMetricStore;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class OpsDashboardQueryService {

    private final OpsMetricStore opsRepository;

    public OpsDashboardQueryService(OpsMetricStore opsRepository) {
        this.opsRepository = opsRepository;
    }

    public List<OpsMetricSummaryView> loadSummary(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsRepository.findSummary(tenantId, fromUtc, toUtc).stream()
            .map(row -> new OpsMetricSummaryView(row.metricKey(), row.metricValue()))
            .toList();
    }

    public List<OpsMetricSeriesView> loadSeries(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsRepository.findSeries(tenantId, fromUtc, toUtc).stream()
            .map(row -> new OpsMetricSeriesView(row.hourBucketUtc(), row.metricKey(), row.metricValue()))
            .toList();
    }

    public record OpsMetricSummaryView(String metricKey, long metricValue) {
    }

    public record OpsMetricSeriesView(Instant hourBucketUtc, String metricKey, long metricValue) {
    }
}
