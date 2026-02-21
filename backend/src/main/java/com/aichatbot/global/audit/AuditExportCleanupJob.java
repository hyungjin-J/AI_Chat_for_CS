package com.aichatbot.global.audit;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AuditExportCleanupJob {

    private final AuditExportJobService auditExportJobService;

    public AuditExportCleanupJob(AuditExportJobService auditExportJobService) {
        this.auditExportJobService = auditExportJobService;
    }

    @Scheduled(cron = "${audit.export.cleanup-cron:0 */5 * * * *}", zone = "UTC")
    public void cleanupExpiredExports() {
        auditExportJobService.cleanupExpiredJobs(200);
    }
}
