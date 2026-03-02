package com.aichatbot.channels.backoffice.presentation;

import com.aichatbot.contexts.knowledge.rag.application.KbAdminService;
import com.aichatbot.contexts.operations.application.OpsEventService;
import com.aichatbot.contexts.operations.audit.AuditLogService;
import com.aichatbot.contexts.identity.security.PrincipalUtils;
import com.aichatbot.contexts.identity.security.UserPrincipal;
import com.aichatbot.platform.error.ApiException;
import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.platform.tenancy.TenantContext;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin/kb")
public class AdminKbController {

    private final KbAdminService kbAdminService;
    private final AuditLogService auditLogService;
    private final OpsEventService opsEventService;

    public AdminKbController(
        KbAdminService kbAdminService,
        AuditLogService auditLogService,
        OpsEventService opsEventService
    ) {
        this.kbAdminService = kbAdminService;
        this.auditLogService = auditLogService;
        this.opsEventService = opsEventService;
    }

    @PostMapping("/documents")
    public ResponseEntity<KbDocumentResponse> uploadDocument(
        @Valid @RequestBody KbDocumentUploadRequest request,
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        UUID traceId = parseRequiredUuid(TraceGuard.requireTraceId(), "invalid_trace_id");

        KbAdminService.KbDocumentView created = kbAdminService.createDocument(
            tenantId,
            request.title(),
            request.sourceType(),
            request.category(),
            request.effectiveDate(),
            request.owner(),
            request.rawContent(),
            idempotencyKey,
            traceId
        );

        opsEventService.append(
            tenantId,
            "KB_DOCUMENT_UPLOADED",
            "audit_export_requested",
            1L,
            Map.of("document_id", created.documentId().toString())
        );
        auditLogService.write(
            tenantId,
            "KB_DOCUMENT_UPLOADED",
            actorUserId,
            String.join(",", principal.roles()),
            "KB_DOCUMENT",
            created.documentId().toString(),
            null,
            request
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(new KbDocumentResponse(
            created.documentId().toString(),
            created.documentVersionId() == null ? null : created.documentVersionId().toString(),
            created.title(),
            created.sourceType(),
            created.category(),
            created.effectiveDate(),
            created.owner(),
            created.versionNo(),
            created.status(),
            created.pipelineStatus(),
            created.pipelineErrorCode(),
            created.pipelineErrorExcerpt(),
            created.indexJobId() == null ? null : created.indexJobId().toString(),
            created.approvedAt(),
            created.updatedAt(),
            TraceGuard.requireTraceId()
        ));
    }

    @GetMapping("/documents")
    public KbDocumentListResponse listDocuments(
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        List<KbDocumentResponse> items = kbAdminService.listDocuments(tenantId, status, limit, offset).stream()
            .map(item -> new KbDocumentResponse(
                item.documentId().toString(),
                item.documentVersionId() == null ? null : item.documentVersionId().toString(),
                item.title(),
                item.sourceType(),
                item.category(),
                item.effectiveDate(),
                item.owner(),
                item.versionNo(),
                item.status(),
                item.pipelineStatus(),
                item.pipelineErrorCode(),
                item.pipelineErrorExcerpt(),
                item.indexJobId() == null ? null : item.indexJobId().toString(),
                item.approvedAt(),
                item.updatedAt(),
                TraceGuard.requireTraceId()
            ))
            .toList();
        return new KbDocumentListResponse(items, Math.max(1, Math.min(200, limit)), Math.max(0, offset), TraceGuard.requireTraceId());
    }

    @PostMapping("/documents/{doc_id}/approve")
    public KbDocumentActionResponse approveDocument(@PathVariable("doc_id") String docId) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID documentId = parseRequiredUuid(docId, "invalid_doc_id");
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        KbAdminService.KbDocumentView updated = kbAdminService.approveDocument(tenantId, documentId);

        auditLogService.write(
            tenantId,
            "KB_DOCUMENT_APPROVED",
            actorUserId,
            String.join(",", principal.roles()),
            "KB_DOCUMENT",
            updated.documentId().toString(),
            null,
            updated
        );

        return new KbDocumentActionResponse(
            updated.documentId().toString(),
            updated.versionNo(),
            updated.status(),
            TraceGuard.requireTraceId()
        );
    }

    @PostMapping("/documents/{doc_id}/versions/{version}/rollback")
    public KbDocumentActionResponse rollbackDocument(
        @PathVariable("doc_id") String docId,
        @PathVariable("version") @Min(1) int version
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID documentId = parseRequiredUuid(docId, "invalid_doc_id");
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        KbAdminService.KbDocumentView updated = kbAdminService.rollbackDocument(tenantId, documentId, version);

        auditLogService.write(
            tenantId,
            "KB_DOCUMENT_ROLLBACK",
            actorUserId,
            String.join(",", principal.roles()),
            "KB_DOCUMENT",
            updated.documentId().toString(),
            null,
            Map.of("version", version)
        );

        return new KbDocumentActionResponse(
            updated.documentId().toString(),
            updated.versionNo(),
            "rolled_back",
            TraceGuard.requireTraceId()
        );
    }

    @PostMapping("/reindex")
    public ResponseEntity<KbReindexJobResponse> requestReindex(
        @RequestBody(required = false) KbReindexRequest request,
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        UUID traceId = parseRequiredUuid(TraceGuard.requireTraceId(), "invalid_trace_id");
        KbAdminService.KbReindexJobView job = kbAdminService.requestReindex(
            tenantId,
            actorUserId,
            request == null ? null : request.note(),
            idempotencyKey,
            traceId
        );

        auditLogService.write(
            tenantId,
            "KB_REINDEX_REQUESTED",
            actorUserId,
            String.join(",", principal.roles()),
            "KB_REINDEX_JOB",
            job.jobId().toString(),
            null,
            request
        );

        return ResponseEntity.status(HttpStatus.ACCEPTED).body(toReindexResponse(job));
    }

    @GetMapping("/reindex/{job_id}")
    public KbReindexJobResponse getReindexStatus(@PathVariable("job_id") String jobId) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID targetJobId = parseRequiredUuid(jobId, "invalid_job_id");
        KbAdminService.KbReindexJobView job = kbAdminService.getReindexStatus(tenantId, targetJobId);
        return toReindexResponse(job);
    }

    @GetMapping("/index-operations")
    public KbReindexOperationListResponse listIndexOperations(
        @RequestParam(value = "limit", defaultValue = "20") int limit
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        List<KbReindexJobResponse> items = kbAdminService.listIndexOperations(tenantId, limit).stream()
            .map(this::toReindexResponse)
            .toList();
        return new KbReindexOperationListResponse(items, Math.max(1, Math.min(200, limit)), TraceGuard.requireTraceId());
    }

    private KbReindexJobResponse toReindexResponse(KbAdminService.KbReindexJobView job) {
        return new KbReindexJobResponse(
            job.jobId().toString(),
            job.jobType(),
            job.documentVersionId() == null ? null : job.documentVersionId().toString(),
            job.idempotencyKey(),
            job.status(),
            job.attemptCount(),
            job.maxAttempts(),
            job.nextRetryAt(),
            job.errorCode(),
            job.errorExcerpt(),
            job.requestedBy() == null ? null : job.requestedBy().toString(),
            job.requestedAt(),
            job.startedAt(),
            job.completedAt(),
            job.resultMessage(),
            job.lastTraceId() == null ? null : job.lastTraceId().toString(),
            TraceGuard.requireTraceId()
        );
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

    public record KbDocumentUploadRequest(
        @NotBlank
        String title,
        String sourceType,
        String category,
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        LocalDate effectiveDate,
        String owner,
        String rawContent
    ) {
    }

    public record KbDocumentResponse(
        String documentId,
        String documentVersionId,
        String title,
        String sourceType,
        String category,
        LocalDate effectiveDate,
        String owner,
        int versionNo,
        String status,
        String pipelineStatus,
        String pipelineErrorCode,
        String pipelineErrorExcerpt,
        String indexJobId,
        java.time.Instant approvedAt,
        java.time.Instant updatedAt,
        String traceId
    ) {
    }

    public record KbDocumentListResponse(
        List<KbDocumentResponse> items,
        int limit,
        int offset,
        String traceId
    ) {
    }

    public record KbDocumentActionResponse(
        String documentId,
        int versionNo,
        String result,
        String traceId
    ) {
    }

    public record KbReindexRequest(
        String note
    ) {
    }

    public record KbReindexJobResponse(
        String jobId,
        String jobType,
        String documentVersionId,
        String idempotencyKey,
        String status,
        Integer attemptCount,
        Integer maxAttempts,
        java.time.Instant nextRetryAt,
        String errorCode,
        String errorExcerpt,
        String requestedBy,
        java.time.Instant requestedAt,
        java.time.Instant startedAt,
        java.time.Instant completedAt,
        String resultMessage,
        String lastTraceId,
        String traceId
    ) {
    }

    public record KbReindexOperationListResponse(
        List<KbReindexJobResponse> items,
        int limit,
        String traceId
    ) {
    }
}
