package com.aichatbot.admin.presentation;

import com.aichatbot.global.audit.AuditLogService;
import com.aichatbot.global.audit.AuditChainVerifierService;
import com.aichatbot.global.audit.AuditExportJobService;
import com.aichatbot.global.audit.domain.AuditExportJobRecord;
import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.ops.domain.OpsMetricRow;
import com.aichatbot.ops.domain.OpsMetricTotal;
import com.aichatbot.ops.infrastructure.OpsRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin")
public class AdminOpsDashboardController {

    private final OpsRepository opsRepository;
    private final AuditLogService auditLogService;
    private final AuditChainVerifierService auditChainVerifierService;
    private final AuditExportJobService auditExportJobService;

    public AdminOpsDashboardController(
        OpsRepository opsRepository,
        AuditLogService auditLogService,
        AuditChainVerifierService auditChainVerifierService,
        AuditExportJobService auditExportJobService
    ) {
        this.opsRepository = opsRepository;
        this.auditLogService = auditLogService;
        this.auditChainVerifierService = auditChainVerifierService;
        this.auditExportJobService = auditExportJobService;
    }

    @GetMapping("/dashboard/summary")
    public DashboardSummaryResponse summary(
        @RequestParam(value = "tenant_id", required = false) String tenantId,
        @RequestParam(value = "from_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc
    ) {
        UUID resolvedTenantId = resolveTenantScope(tenantId);
        List<OpsMetricTotal> rows = opsRepository.findSummary(resolvedTenantId, fromUtc, toUtc);
        Map<String, Long> totals = new LinkedHashMap<>();
        for (OpsMetricTotal row : rows) {
            totals.put(row.metricKey(), row.metricValue());
        }
        return new DashboardSummaryResponse(
            resolvedTenantId.toString(),
            totals,
            TraceGuard.requireTraceId()
        );
    }

    @GetMapping("/dashboard/series")
    public DashboardSeriesResponse series(
        @RequestParam(value = "tenant_id", required = false) String tenantId,
        @RequestParam(value = "from_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc
    ) {
        UUID resolvedTenantId = resolveTenantScope(tenantId);
        List<OpsMetricRow> series = opsRepository.findSeries(resolvedTenantId, fromUtc, toUtc);
        List<SeriesPoint> points = series.stream()
            .map(row -> new SeriesPoint(row.hourBucketUtc(), row.metricKey(), row.metricValue()))
            .toList();
        return new DashboardSeriesResponse(
            resolvedTenantId.toString(),
            points,
            TraceGuard.requireTraceId()
        );
    }

    @GetMapping("/audit-logs")
    public AuditLogSearchResponse auditLogs(
        @RequestParam(value = "tenant_id", required = false) String tenantId,
        @RequestParam(value = "from_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc,
        @RequestParam(value = "actor_user_id", required = false) String actorUserId,
        @RequestParam(value = "action_type", required = false) String actionType,
        @RequestParam(value = "trace_id", required = false) String traceId,
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID resolvedTenantId = resolveTenantScope(tenantId);
        UUID actorUserUuid = parseUuidOrNull(actorUserId);
        UUID traceUuid = parseUuidOrNull(traceId);
        int safeLimit = Math.max(1, Math.min(200, limit));
        int safeOffset = Math.max(0, offset);
        List<PersistentAuditLogEntry> entries = auditLogService.search(
            resolvedTenantId,
            fromUtc,
            toUtc,
            actorUserUuid,
            actionType,
            traceUuid,
            safeLimit,
            safeOffset
        );
        List<AuditLogItem> items = entries.stream()
            .map(entry -> new AuditLogItem(
                entry.id().toString(),
                entry.actionType(),
                entry.actorUserId() == null ? null : entry.actorUserId().toString(),
                entry.actorRole(),
                entry.targetType(),
                entry.targetId(),
                entry.traceId().toString(),
                entry.createdAt()
            ))
            .toList();
        return new AuditLogSearchResponse(
            resolvedTenantId.toString(),
            items,
            safeLimit,
            safeOffset,
            TraceGuard.requireTraceId()
        );
    }

    @GetMapping("/audit-logs/{audit_id}/diff")
    public AuditLogDiffResponse auditDiff(@PathVariable("audit_id") String auditId) {
        UUID auditUuid = parseRequiredUuid(auditId, "invalid_audit_id");
        UUID contextTenantId = parseRequiredUuid(TenantContext.getTenantId(), "invalid_tenant_context");
        PersistentAuditLogEntry entry = auditLogService.findById(auditUuid)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", "Audit log not found"));
        if (!contextTenantId.equals(entry.tenantId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "SEC-002-403", "Tenant scope mismatch");
        }
        return new AuditLogDiffResponse(
            entry.id().toString(),
            entry.beforeJson(),
            entry.afterJson(),
            entry.traceId().toString(),
            TraceGuard.requireTraceId()
        );
    }

    @GetMapping("/audit-logs/export")
    public ResponseEntity<String> exportAuditLogs(
        @RequestParam(value = "tenant_id", required = false) String tenantId,
        @RequestParam(value = "format", defaultValue = "json") String format,
        @RequestParam(value = "from_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc,
        @RequestParam(value = "limit", defaultValue = "1000") int limit
    ) {
        UUID resolvedTenantId = resolveTenantScope(tenantId);
        int safeLimit = Math.max(1, Math.min(5000, limit));
        if (fromUtc != null && toUtc != null && ChronoUnit.DAYS.between(fromUtc, toUtc) > 31) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "AUDIT_EXPORT_RANGE_EXCEEDED",
                "Audit export range must be 31 days or less",
                List.of("range_exceeded")
            );
        }

        List<PersistentAuditLogEntry> entries = auditLogService.search(
            resolvedTenantId,
            fromUtc,
            toUtc,
            null,
            null,
            null,
            safeLimit,
            0
        );

        String normalizedFormat = format == null ? "json" : format.trim().toLowerCase();
        String body;
        String filename;
        MediaType mediaType;
        if ("csv".equals(normalizedFormat)) {
            body = toCsv(entries);
            filename = "audit_export.csv";
            mediaType = MediaType.TEXT_PLAIN;
        } else {
            body = toJson(entries);
            filename = "audit_export.json";
            mediaType = MediaType.APPLICATION_JSON;
        }
        auditLogService.writeExportLog(
            resolvedTenantId,
            AuditLogService.toUuidOrNull(com.aichatbot.global.security.PrincipalUtils.currentPrincipal().userId()),
            normalizedFormat,
            fromUtc,
            toUtc,
            entries.size()
        );
        return ResponseEntity.ok()
            .contentType(mediaType)
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
            .body(body);
    }

    @PostMapping("/audit-logs/export-jobs")
    public ResponseEntity<AuditExportJobCreateResponse> createAuditExportJob(
        @RequestBody(required = false) AuditExportJobCreateRequest request
    ) {
        UUID tenantId = parseRequiredUuid(TenantContext.getTenantId(), "invalid_tenant_context");
        AuditExportJobRecord created = auditExportJobService.createJob(
            tenantId,
            AuditLogService.toUuidOrNull(PrincipalUtils.currentPrincipal().userId()),
            request == null ? null : request.format(),
            request == null ? null : request.fromUtc(),
            request == null ? null : request.toUtc(),
            request == null ? null : request.rowLimit(),
            request == null ? null : request.maxBytes(),
            request == null ? null : request.maxDurationSec()
        );
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(
            new AuditExportJobCreateResponse(
                created.id().toString(),
                created.status(),
                created.expiresAt(),
                TraceGuard.requireTraceId()
            )
        );
    }

    @GetMapping("/audit-logs/export-jobs/{job_id}")
    public AuditExportJobStatusResponse getAuditExportJob(@PathVariable("job_id") String jobId) {
        UUID tenantId = parseRequiredUuid(TenantContext.getTenantId(), "invalid_tenant_context");
        UUID exportJobId = parseRequiredUuid(jobId, "invalid_export_job_id");
        AuditExportJobRecord job = auditExportJobService.findById(tenantId, exportJobId);
        return new AuditExportJobStatusResponse(
            job.id().toString(),
            job.status(),
            job.exportFormat(),
            job.rowCount(),
            job.totalBytes(),
            job.errorCode(),
            job.errorMessage(),
            job.createdAt(),
            job.completedAt(),
            job.expiresAt(),
            TraceGuard.requireTraceId()
        );
    }

    @GetMapping("/audit-logs/export-jobs/{job_id}/download")
    public ResponseEntity<byte[]> downloadAuditExportJob(@PathVariable("job_id") String jobId) {
        UUID tenantId = parseRequiredUuid(TenantContext.getTenantId(), "invalid_tenant_context");
        UUID exportJobId = parseRequiredUuid(jobId, "invalid_export_job_id");
        AuditExportJobService.DownloadPayload payload = auditExportJobService.download(
            tenantId,
            exportJobId,
            AuditLogService.toUuidOrNull(PrincipalUtils.currentPrincipal().userId())
        );
        String format = payload.job().exportFormat();
        String filename = "audit_export_" + payload.job().id() + "." + format;
        MediaType mediaType = "csv".equals(format) ? MediaType.TEXT_PLAIN : MediaType.APPLICATION_JSON;
        return ResponseEntity.ok()
            .contentType(mediaType)
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
            .body(payload.payload());
    }

    @GetMapping("/audit-logs/chain-verify")
    public AuditChainVerifyResponse verifyAuditChain(
        @RequestParam(value = "tenant_id", required = false) String tenantId,
        @RequestParam(value = "from_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc,
        @RequestParam(value = "limit", defaultValue = "1000") int limit
    ) {
        if (fromUtc != null && toUtc != null && fromUtc.isAfter(toUtc)) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                "from_utc must be before to_utc",
                List.of("invalid_time_range")
            );
        }
        UUID resolvedTenantId = resolveTenantScope(tenantId);
        AuditChainVerifierService.AuditChainVerificationResult result = auditChainVerifierService.verify(
            resolvedTenantId,
            fromUtc,
            toUtc,
            limit
        );
        return new AuditChainVerifyResponse(
            resolvedTenantId.toString(),
            result.passed(),
            result.checkedRows(),
            result.failureCount(),
            result.failureSamples(),
            result.verifiedAt(),
            result.traceId()
        );
    }

    private UUID resolveTenantScope(String tenantId) {
        UUID contextTenantId = parseRequiredUuid(TenantContext.getTenantId(), "invalid_tenant_context");
        if (tenantId == null || tenantId.isBlank()) {
            return contextTenantId;
        }
        UUID requested = parseRequiredUuid(tenantId, "invalid_tenant_id");
        if (!contextTenantId.equals(requested)) {
            throw new ApiException(HttpStatus.FORBIDDEN, "SEC-002-403", "Tenant scope mismatch");
        }
        return requested;
    }

    private UUID parseUuidOrNull(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(rawValue.trim());
        } catch (IllegalArgumentException exception) {
            return null;
        }
    }

    private UUID parseRequiredUuid(String rawValue, String detail) {
        try {
            return UUID.fromString(rawValue);
        } catch (Exception exception) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                "UUID format is invalid",
                List.of(detail)
            );
        }
    }

    public record DashboardSummaryResponse(
        String tenantId,
        Map<String, Long> totals,
        String traceId
    ) {
    }

    public record SeriesPoint(
        Instant hourBucketUtc,
        String metricKey,
        long metricValue
    ) {
    }

    public record DashboardSeriesResponse(
        String tenantId,
        List<SeriesPoint> series,
        String traceId
    ) {
    }

    public record AuditLogItem(
        String auditId,
        String actionType,
        String actorUserId,
        String actorRole,
        String targetType,
        String targetId,
        String traceId,
        Instant createdAt
    ) {
    }

    public record AuditLogSearchResponse(
        String tenantId,
        List<AuditLogItem> items,
        int limit,
        int offset,
        String traceId
    ) {
    }

    public record AuditLogDiffResponse(
        String auditId,
        String beforeJson,
        String afterJson,
        String sourceTraceId,
        String traceId
    ) {
    }

    public record AuditChainVerifyResponse(
        String tenantId,
        boolean passed,
        int checkedRows,
        int failureCount,
        List<String> failureSamples,
        Instant verifiedAt,
        String traceId
    ) {
    }

    public record AuditExportJobCreateRequest(
        String format,
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant fromUtc,
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant toUtc,
        Integer rowLimit,
        Integer maxBytes,
        Integer maxDurationSec
    ) {
    }

    public record AuditExportJobCreateResponse(
        String jobId,
        String status,
        Instant expiresAt,
        String traceId
    ) {
    }

    public record AuditExportJobStatusResponse(
        String jobId,
        String status,
        String format,
        int rowCount,
        int totalBytes,
        String errorCode,
        String errorMessage,
        Instant createdAt,
        Instant completedAt,
        Instant expiresAt,
        String traceId
    ) {
    }

    private String toJson(List<PersistentAuditLogEntry> entries) {
        StringBuilder builder = new StringBuilder();
        builder.append("[");
        for (int index = 0; index < entries.size(); index++) {
            PersistentAuditLogEntry entry = entries.get(index);
            if (index > 0) {
                builder.append(",");
            }
            builder.append("{")
                .append("\"audit_id\":\"").append(entry.id()).append("\",")
                .append("\"action_type\":\"").append(entry.actionType()).append("\",")
                .append("\"actor_user_id\":").append(entry.actorUserId() == null ? "null" : "\"" + entry.actorUserId() + "\"").append(",")
                .append("\"trace_id\":\"").append(entry.traceId()).append("\",")
                .append("\"created_at\":\"").append(entry.createdAt()).append("\",")
                .append("\"before_json\":").append(entry.beforeJson() == null ? "null" : "\"" + escapeJson(entry.beforeJson()) + "\"").append(",")
                .append("\"after_json\":").append(entry.afterJson() == null ? "null" : "\"" + escapeJson(entry.afterJson()) + "\"")
                .append("}");
        }
        builder.append("]");
        return builder.toString();
    }

    private String toCsv(List<PersistentAuditLogEntry> entries) {
        StringBuilder builder = new StringBuilder();
        builder.append("audit_id,action_type,actor_user_id,trace_id,created_at,target_type,target_id,chain_seq").append("\n");
        for (PersistentAuditLogEntry entry : entries) {
            builder.append(entry.id()).append(",")
                .append(csv(entry.actionType())).append(",")
                .append(entry.actorUserId() == null ? "" : entry.actorUserId()).append(",")
                .append(entry.traceId()).append(",")
                .append(entry.createdAt()).append(",")
                .append(csv(entry.targetType())).append(",")
                .append(csv(entry.targetId())).append(",")
                .append(entry.chainSeq() == null ? "" : entry.chainSeq())
                .append("\n");
        }
        return builder.toString();
    }

    private String csv(String value) {
        if (value == null) {
            return "";
        }
        String escaped = value.replace("\"", "\"\"");
        return "\"" + escaped + "\"";
    }

    private String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
