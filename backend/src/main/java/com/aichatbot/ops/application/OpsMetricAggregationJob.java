package com.aichatbot.ops.application;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import com.aichatbot.global.scheduler.SchedulerLockService;

@Component
public class OpsMetricAggregationJob {

    private final OpsMetricAggregationService opsMetricAggregationService;
    private final SchedulerLockService schedulerLockService;

    public OpsMetricAggregationJob(OpsMetricAggregationService opsMetricAggregationService, SchedulerLockService schedulerLockService) {
        this.opsMetricAggregationService = opsMetricAggregationService;
        this.schedulerLockService = schedulerLockService;
    }

    @Scheduled(cron = "${ops.metric.hourly-aggregation-cron:0 * * * * *}", zone = "UTC")
    public void aggregateHourly() {
        if (!schedulerLockService.tryAcquire("ops_metric_hourly_aggregation", java.time.Duration.ofSeconds(90))) {
            return;
        }
        opsMetricAggregationService.aggregateHourlyUtcWindow();
    }
}
