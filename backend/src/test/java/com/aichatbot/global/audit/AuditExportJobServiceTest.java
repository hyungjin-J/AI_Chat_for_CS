package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.AuditExportJobRecord;
import com.aichatbot.global.audit.export.ExportStorage;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.ops.application.OpsEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AuditExportJobServiceTest {

    private final PersistentAuditLogRepository auditLogRepository = mock(PersistentAuditLogRepository.class);
    private final AuditLogService auditLogService = mock(AuditLogService.class);
    private final AuditSanitizer auditSanitizer = new AuditSanitizer(new ObjectMapper());
    private final ExportStorage exportStorage = mock(ExportStorage.class);
    private final OpsEventService opsEventService = mock(OpsEventService.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Clock clock = Clock.fixed(Instant.parse("2026-03-10T12:00:00Z"), ZoneOffset.UTC);

    private AuditExportJobService service;

    @BeforeEach
    void setUp() {
        TraceContext.setTraceId("90000000-0000-4000-8000-000000000001");
        service = new AuditExportJobService(
            auditLogRepository,
            auditLogService,
            auditSanitizer,
            exportStorage,
            opsEventService,
            objectMapper,
            clock
        );
    }

    @AfterEach
    void tearDown() {
        TraceContext.clear();
    }

    @Test
    void createJobShouldPersistPendingJob() {
        UUID tenantId = UUID.fromString("90000000-0000-4000-8000-000000000002");
        UUID jobId = UUID.fromString("90000000-0000-4000-8000-000000000003");
        AuditExportJobRecord pending = new AuditExportJobRecord(
            jobId,
            tenantId,
            UUID.fromString("90000000-0000-4000-8000-000000000004"),
            "PENDING",
            "json",
            Instant.parse("2026-03-10T00:00:00Z"),
            Instant.parse("2026-03-10T01:00:00Z"),
            1000,
            1024 * 1024,
            20,
            0,
            0,
            null,
            null,
            Instant.parse("2026-03-11T12:00:00Z"),
            Instant.parse("2026-03-10T12:00:00Z"),
            null,
            null,
            UUID.fromString("90000000-0000-4000-8000-000000000001")
        );

        when(auditLogRepository.findExportJobById(eq(tenantId), any())).thenReturn(Optional.of(pending));

        AuditExportJobRecord created = service.createJob(
            tenantId,
            pending.requestedBy(),
            "json",
            pending.fromUtc(),
            pending.toUtc(),
            1000,
            1024 * 1024,
            20
        );

        assertThat(created.status()).isEqualTo("PENDING");
        verify(auditLogRepository).insertExportJob(any(), eq(tenantId), any(), eq("PENDING"), eq("json"), any(), any(), eq(1000), eq(1024 * 1024), eq(20), any(), any(), any());
    }

    @Test
    void downloadShouldRejectNotReadyJob() {
        UUID tenantId = UUID.fromString("90000000-0000-4000-8000-000000000002");
        UUID jobId = UUID.fromString("90000000-0000-4000-8000-000000000005");
        AuditExportJobRecord running = new AuditExportJobRecord(
            jobId,
            tenantId,
            null,
            "RUNNING",
            "json",
            null,
            null,
            1000,
            10000,
            20,
            0,
            0,
            null,
            null,
            Instant.parse("2026-03-10T16:00:00Z"),
            Instant.parse("2026-03-10T12:00:00Z"),
            Instant.parse("2026-03-10T12:01:00Z"),
            null,
            UUID.fromString("90000000-0000-4000-8000-000000000001")
        );
        when(auditLogRepository.findExportJobById(tenantId, jobId)).thenReturn(Optional.of(running));

        assertThatThrownBy(() -> service.download(tenantId, jobId, null))
            .hasMessageContaining("not ready");
    }

    @Test
    void cleanupExpiredJobsShouldMarkExpiredAndDeletePayload() {
        UUID tenantId = UUID.fromString("90000000-0000-4000-8000-000000000010");
        UUID jobId = UUID.fromString("90000000-0000-4000-8000-000000000011");
        AuditExportJobRecord doneJob = new AuditExportJobRecord(
            jobId,
            tenantId,
            null,
            "DONE",
            "csv",
            null,
            null,
            1000,
            1024 * 1024,
            20,
            5,
            1200,
            null,
            null,
            Instant.parse("2026-03-09T11:00:00Z"),
            Instant.parse("2026-03-09T10:00:00Z"),
            Instant.parse("2026-03-09T10:01:00Z"),
            Instant.parse("2026-03-09T10:02:00Z"),
            UUID.fromString("90000000-0000-4000-8000-000000000001")
        );
        when(auditLogRepository.findJobsToExpire(any(), anyInt())).thenReturn(java.util.List.of(doneJob));
        when(auditLogRepository.markExportJobExpired(eq(jobId), any())).thenReturn(true);

        int expired = service.cleanupExpiredJobs(100);

        assertThat(expired).isEqualTo(1);
        verify(exportStorage).expireJobPayload(jobId);
        verify(opsEventService).append(eq(tenantId), eq("AUDIT_EXPORT_EXPIRED"), eq("audit_export_expired"), eq(1L), any());
        verify(auditLogService).write(eq(tenantId), eq("AUDIT_EXPORT_EXPIRED"), any(), anyString(), eq("AUDIT_EXPORT_JOB"), eq(jobId.toString()), any(), any());
    }
}
