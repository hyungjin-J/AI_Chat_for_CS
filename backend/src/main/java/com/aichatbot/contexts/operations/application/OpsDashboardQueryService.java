package com.aichatbot.contexts.operations.application;

import com.aichatbot.contexts.operations.domain.OpsMetricRow;
import com.aichatbot.contexts.operations.domain.OpsMetricTotal;
import com.aichatbot.contexts.operations.infrastructure.OpsRepository;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class OpsDashboardQueryService {

    private final OpsRepository opsRepository;

    public OpsDashboardQueryService(OpsRepository opsRepository) {
        this.opsRepository = opsRepository;
    }

    public List<OpsMetricTotal> loadSummary(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsRepository.findSummary(tenantId, fromUtc, toUtc);
    }

    public List<OpsMetricRow> loadSeries(UUID tenantId, Instant fromUtc, Instant toUtc) {
        return opsRepository.findSeries(tenantId, fromUtc, toUtc);
    }
}
