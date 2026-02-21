package com.aichatbot.global.audit;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AuditExportWorkerJob {

    private final AuditExportJobService auditExportJobService;

    public AuditExportWorkerJob(AuditExportJobService auditExportJobService) {
        this.auditExportJobService = auditExportJobService;
    }

    @Scheduled(cron = "${audit.export.worker-cron:*/15 * * * * *}", zone = "UTC")
    public void processPendingExports() {
        auditExportJobService.processPendingJobs(20);
    }
}
