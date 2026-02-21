package com.aichatbot.ops.application;

import com.aichatbot.ops.domain.OpsMetricTotal;
import com.aichatbot.ops.infrastructure.OpsRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock"
})
class OpsMetricAggregationContractTest {

    @Autowired
    private OpsRepository opsRepository;

    @Autowired
    private OpsMetricAggregationService opsMetricAggregationService;

    @Test
    void shouldAggregateAllowlistMetricsIdempotentlyInUtcBucket() {
        UUID tenantId = UUID.fromString("00000000-0000-0000-0000-00000000000a");
        Instant hour = Instant.now().truncatedTo(ChronoUnit.HOURS);

        opsRepository.insertOpsEvent(
            UUID.randomUUID(),
            tenantId,
            UUID.fromString("85000000-0000-4000-8000-000000000001"),
            hour.plusSeconds(120),
            "AUTH_LOGIN_SUCCESS",
            "auth_login_success",
            2L,
            "{}"
        );
        opsRepository.insertOpsEvent(
            UUID.randomUUID(),
            tenantId,
            UUID.fromString("85000000-0000-4000-8000-000000000002"),
            hour.plusSeconds(180),
            "UNKNOWN_EVENT",
            "unknown_metric_key",
            9L,
            "{}"
        );

        opsMetricAggregationService.aggregateHourlyUtcWindow();
        opsMetricAggregationService.aggregateHourlyUtcWindow();

        List<OpsMetricTotal> summary = opsRepository.findSummary(tenantId, hour.minus(1, ChronoUnit.HOURS), hour.plus(2, ChronoUnit.HOURS));
        assertThat(summary.stream().anyMatch(row -> row.metricKey().equals("unknown_metric_key"))).isFalse();
        assertThat(summary.stream()
            .filter(row -> row.metricKey().equals("auth_login_success"))
            .findFirst()
            .map(OpsMetricTotal::metricValue)
            .orElse(0L)).isEqualTo(2L);
    }
}
