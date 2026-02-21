package com.aichatbot.ops.application;

import com.aichatbot.ops.domain.OpsEventAggregate;
import com.aichatbot.ops.infrastructure.OpsRepository;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class OpsMetricAggregationService {

    private final OpsRepository opsRepository;
    private final OpsEventService opsEventService;
    private final Clock clock;

    @Autowired
    public OpsMetricAggregationService(OpsRepository opsRepository, OpsEventService opsEventService) {
        this(opsRepository, opsEventService, Clock.systemUTC());
    }

    OpsMetricAggregationService(OpsRepository opsRepository, OpsEventService opsEventService, Clock clock) {
        this.opsRepository = opsRepository;
        this.opsEventService = opsEventService;
        this.clock = clock;
    }

    public void aggregateHourlyUtcWindow() {
        Instant nowUtc = Instant.now(clock);
        Instant fromUtc = nowUtc.truncatedTo(ChronoUnit.HOURS).minus(1, ChronoUnit.HOURS);
        Instant toUtc = nowUtc.truncatedTo(ChronoUnit.HOURS).plus(1, ChronoUnit.HOURS);
        List<OpsEventAggregate> aggregates = opsRepository.aggregateHourly(
            fromUtc,
            toUtc,
            opsEventService.metricKeyAllowlist()
        );
        Instant updatedAt = Instant.now(clock);
        for (OpsEventAggregate row : aggregates) {
            if (!opsEventService.isAllowlistedMetricKey(row.metricKey())) {
                continue;
            }
            opsRepository.upsertHourlyMetric(
                row.tenantId(),
                row.hourBucketUtc(),
                row.metricKey(),
                row.metricValue(),
                updatedAt
            );
        }
    }
}
