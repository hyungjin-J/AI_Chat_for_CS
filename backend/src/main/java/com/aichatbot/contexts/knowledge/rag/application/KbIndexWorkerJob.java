package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.operations.scheduler.SchedulerLockService;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class KbIndexWorkerJob {

    private final KbIndexPipelineService kbIndexPipelineService;
    private final SchedulerLockService schedulerLockService;
    private final int batchLimit;

    public KbIndexWorkerJob(
        KbIndexPipelineService kbIndexPipelineService,
        SchedulerLockService schedulerLockService,
        @Value("${kb.index.worker.batch-limit:20}") int batchLimit
    ) {
        this.kbIndexPipelineService = kbIndexPipelineService;
        this.schedulerLockService = schedulerLockService;
        this.batchLimit = Math.max(1, batchLimit);
    }

    @Scheduled(cron = "${kb.index.worker-cron:*/20 * * * * *}", zone = "UTC")
    public void processPendingJobs() {
        if (!schedulerLockService.tryAcquire("kb_index_pipeline_worker", Duration.ofSeconds(90))) {
            return;
        }
        kbIndexPipelineService.processPendingJobs(batchLimit);
    }
}

