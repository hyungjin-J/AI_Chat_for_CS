package com.aichatbot.channels.backoffice.presentation;

import com.aichatbot.contexts.operations.application.BackofficeAdminService;
import com.aichatbot.contexts.operations.audit.AuditLogService;
import com.aichatbot.contexts.identity.security.PrincipalUtils;
import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.platform.tenancy.TenantContext;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/ops")
public class OpsAdminController {

    private final BackofficeAdminService backofficeAdminService;
    private final AuditLogService auditLogService;

    public OpsAdminController(BackofficeAdminService backofficeAdminService, AuditLogService auditLogService) {
        this.backofficeAdminService = backofficeAdminService;
        this.auditLogService = auditLogService;
    }

    @GetMapping("/llm/providers/health")
    public ProviderHealthResponse listProviderHealth() {
        UUID tenantId = currentTenantId();
        List<ProviderHealthItem> items = backofficeAdminService.listProviderHealth(tenantId).stream()
            .map(view -> new ProviderHealthItem(view.provider(), view.healthStatus(), view.killSwitch(), view.updatedAt()))
            .toList();
        return new ProviderHealthResponse(items, TraceGuard.requireTraceId());
    }

    @PostMapping("/llm/providers/{provider}/kill-switch")
    public ResponseEntity<AdminConfigController.ResourceResponse> setKillSwitch(
        @PathVariable("provider") String provider,
        @RequestBody(required = false) KillSwitchRequest request
    ) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        boolean enabled = request != null && request.enabled();
        BackofficeAdminService.AdminResourceView updated = backofficeAdminService.setProviderKillSwitch(
            tenantId,
            actorUserId,
            provider,
            enabled
        );
        writeAudit(tenantId, actorUserId, "PROVIDER_KILL_SWITCH", "PROVIDER_CONFIG", provider, request);
        AdminConfigController.ResourceResponse response = new AdminConfigController.ResourceResponse(
            updated.resourceKey(),
            updated.status(),
            updated.activeFlag(),
            updated.payloadJson(),
            updated.lastRotatedAt(),
            updated.updatedAt(),
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.ok(response);
    }

    @GetMapping("/traces")
    public OpsTraceListResponse queryTraces(
        @RequestParam(value = "keyword", required = false) String keyword,
        @RequestParam(value = "from", required = false) Instant fromUtc,
        @RequestParam(value = "to", required = false) Instant toUtc,
        @RequestParam(value = "limit", defaultValue = "100") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = currentTenantId();
        List<OpsTraceItem> items = backofficeAdminService.queryTraces(
            tenantId,
            keyword,
            fromUtc,
            toUtc,
            limit,
            offset
        ).stream().map(row -> new OpsTraceItem(
            row.eventId().toString(),
            row.traceId().toString(),
            row.eventType(),
            row.metricKey(),
            row.metricValue(),
            row.dimensionsJson(),
            row.eventTime()
        )).toList();
        return new OpsTraceListResponse(items, TraceGuard.requireTraceId());
    }

    @GetMapping("/metrics/summary")
    public OpsMetricSummaryResponse metricSummary(
        @RequestParam(value = "from_utc", required = false) Instant fromUtc,
        @RequestParam(value = "to_utc", required = false) Instant toUtc
    ) {
        UUID tenantId = currentTenantId();
        List<OpsMetricSummaryItem> items = backofficeAdminService.summarizeMetrics(tenantId, fromUtc, toUtc).stream()
            .map(row -> new OpsMetricSummaryItem(row.metricKey(), row.metricValue()))
            .toList();
        return new OpsMetricSummaryResponse(items, TraceGuard.requireTraceId());
    }

    @PostMapping("/rollbacks")
    public ResponseEntity<OpsRollbackResponse> triggerRollback(@RequestBody(required = false) OpsRollbackRequest request) {
        UUID tenantId = currentTenantId();
        UUID actorUserId = currentActorUserId();
        BackofficeAdminService.OpsRollbackView created = backofficeAdminService.triggerRollback(
            tenantId,
            actorUserId,
            request == null ? null : request.targetType(),
            request == null ? null : request.targetId(),
            request == null ? null : request.reason()
        );
        writeAudit(tenantId, actorUserId, "OPS_ROLLBACK_TRIGGER", "ROLLBACK", created.rollbackId().toString(), request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(
            new OpsRollbackResponse(created.rollbackId().toString(), created.status(), created.createdAt(), TraceGuard.requireTraceId())
        );
    }

    @GetMapping("/workflow/reports")
    public WorkflowReportResponse workflowReport() {
        UUID tenantId = currentTenantId();
        BackofficeAdminService.WorkflowReportView report = backofficeAdminService.workflowReport(tenantId);
        List<BackofficeAdminService.OpsRollbackListItemView> rollbacks = backofficeAdminService.listRecentRollbacks(tenantId, 20);
        List<OpsRollbackItem> items = rollbacks.stream()
            .map(row -> new OpsRollbackItem(
                row.rollbackId().toString(),
                row.targetType(),
                row.targetId(),
                row.status(),
                row.reason(),
                row.createdAt()
            ))
            .toList();
        return new WorkflowReportResponse(report.recentRollbackCount(), report.recentTargets(), items, TraceGuard.requireTraceId());
    }

    @GetMapping("/mcp/servers/{server_id}/health")
    public MpcServerHealthResponse mcpServerHealth(@PathVariable("server_id") String serverId) {
        return new MpcServerHealthResponse(
            serverId,
            "healthy",
            "available",
            TraceGuard.requireTraceId()
        );
    }

    private void writeAudit(
        UUID tenantId,
        UUID actorUserId,
        String actionType,
        String targetType,
        String targetId,
        Object payload
    ) {
        auditLogService.write(
            tenantId,
            actionType,
            actorUserId,
            "OPS",
            targetType,
            targetId,
            null,
            payload
        );
    }

    private UUID currentTenantId() {
        return UUID.fromString(TenantContext.getTenantId());
    }

    private UUID currentActorUserId() {
        return AuditLogService.toUuidOrNull(PrincipalUtils.currentPrincipal().userId());
    }

    public record ProviderHealthItem(
        String provider,
        String healthStatus,
        boolean killSwitch,
        Instant updatedAt
    ) {
    }

    public record ProviderHealthResponse(
        List<ProviderHealthItem> items,
        String traceId
    ) {
    }

    public record KillSwitchRequest(
        boolean enabled
    ) {
    }

    public record OpsTraceItem(
        String eventId,
        String traceId,
        String eventType,
        String metricKey,
        long metricValue,
        String dimensionsJson,
        Instant eventTime
    ) {
    }

    public record OpsTraceListResponse(
        List<OpsTraceItem> items,
        String traceId
    ) {
    }

    public record OpsMetricSummaryItem(
        String metricKey,
        long metricValue
    ) {
    }

    public record OpsMetricSummaryResponse(
        List<OpsMetricSummaryItem> items,
        String traceId
    ) {
    }

    public record OpsRollbackRequest(
        String targetType,
        String targetId,
        String reason
    ) {
    }

    public record OpsRollbackResponse(
        String rollbackId,
        String status,
        Instant createdAt,
        String traceId
    ) {
    }

    public record OpsRollbackItem(
        String rollbackId,
        String targetType,
        String targetId,
        String status,
        String reason,
        Instant createdAt
    ) {
    }

    public record WorkflowReportResponse(
        int recentRollbackCount,
        List<String> recentTargets,
        List<OpsRollbackItem> recentRollbacks,
        String traceId
    ) {
    }

    public record MpcServerHealthResponse(
        String serverId,
        String status,
        String detail,
        String traceId
    ) {
    }
}
