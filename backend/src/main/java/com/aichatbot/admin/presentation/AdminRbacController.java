package com.aichatbot.admin.presentation;

import com.aichatbot.admin.infrastructure.RbacApprovalService;
import com.aichatbot.admin.infrastructure.RbacChangeRequestRecord;
import com.aichatbot.global.audit.AuditLogService;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/admin/rbac")
public class AdminRbacController {

    private final RbacApprovalService rbacApprovalService;
    private final AuditLogService auditLogService;

    public AdminRbacController(RbacApprovalService rbacApprovalService, AuditLogService auditLogService) {
        this.rbacApprovalService = rbacApprovalService;
        this.auditLogService = auditLogService;
    }

    @PutMapping("/matrix/{resource_key}")
    public RbacRequestCreateResponse createChangeRequest(
        @PathVariable("resource_key") String resourceKey,
        @Valid @RequestBody RbacMatrixUpsertRequest request
    ) {
        if (resourceKey == null || resourceKey.isBlank()) {
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "API-003-422", "resource_key is required", List.of("resource_key_required"));
        }
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID actorUserId = AuditLogService.toUuidOrNull(principal.userId());
        UUID requestId = rbacApprovalService.createRequest(
            tenantId,
            resourceKey,
            request.roleCode(),
            request.adminLevel(),
            request.allowed(),
            actorUserId,
            request.reason()
        );

        auditLogService.write(
            tenantId,
            "RBAC_CHANGE_REQUEST_CREATED",
            actorUserId,
            String.join(",", principal.roles()),
            "RBAC_CHANGE_REQUEST",
            requestId.toString(),
            null,
            request
        );

        return new RbacRequestCreateResponse("pending", requestId.toString(), TraceGuard.requireTraceId());
    }

    @GetMapping("/approval-requests")
    public RbacRequestListResponse listRequests(
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "limit", defaultValue = "50") int limit,
        @RequestParam(value = "offset", defaultValue = "0") int offset
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        int safeLimit = Math.max(1, Math.min(200, limit));
        int safeOffset = Math.max(0, offset);
        List<RbacChangeRequestRecord> requests = rbacApprovalService.listRequests(tenantId, status, safeLimit, safeOffset);
        List<RbacRequestItem> items = requests.stream()
            .map(record -> new RbacRequestItem(
                record.id().toString(),
                record.resourceKey(),
                record.roleCode(),
                record.adminLevel(),
                record.allowed(),
                record.status(),
                record.requestedBy().toString(),
                record.reason(),
                record.appliedAt(),
                record.createdAt()
            ))
            .toList();
        return new RbacRequestListResponse(items, safeLimit, safeOffset, TraceGuard.requireTraceId());
    }

    @PostMapping("/approval-requests/{request_id}/approve")
    public RbacApprovalActionResponse approve(
        @PathVariable("request_id") String requestId,
        @Valid @RequestBody RbacApprovalActionRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID approver = AuditLogService.toUuidOrNull(principal.userId());
        UUID targetRequestId = parseRequiredUuid(requestId, "invalid_request_id");
        RbacApprovalService.ApprovalResult result = rbacApprovalService.approve(
            tenantId,
            targetRequestId,
            approver,
            principal.adminLevel(),
            request.comment()
        );

        auditLogService.write(
            tenantId,
            "RBAC_CHANGE_REQUEST_APPROVED",
            approver,
            String.join(",", principal.roles()),
            "RBAC_CHANGE_REQUEST",
            requestId,
            null,
            result
        );
        return new RbacApprovalActionResponse(result.status(), result.approvalCount(), result.permissionVersion(), TraceGuard.requireTraceId());
    }

    @PostMapping("/approval-requests/{request_id}/reject")
    public RbacApprovalActionResponse reject(
        @PathVariable("request_id") String requestId,
        @Valid @RequestBody RbacApprovalActionRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID approver = AuditLogService.toUuidOrNull(principal.userId());
        UUID targetRequestId = parseRequiredUuid(requestId, "invalid_request_id");
        rbacApprovalService.reject(tenantId, targetRequestId, approver, principal.adminLevel(), request.comment());
        auditLogService.write(
            tenantId,
            "RBAC_CHANGE_REQUEST_REJECTED",
            approver,
            String.join(",", principal.roles()),
            "RBAC_CHANGE_REQUEST",
            requestId,
            null,
            request
        );
        return new RbacApprovalActionResponse("REJECTED", 0, null, TraceGuard.requireTraceId());
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

    public record RbacMatrixUpsertRequest(
        @NotBlank
        String roleCode,
        @NotBlank
        String adminLevel,
        boolean allowed,
        String reason
    ) {
    }

    public record RbacRequestCreateResponse(
        String result,
        String requestId,
        String traceId
    ) {
    }

    public record RbacRequestItem(
        String requestId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        String status,
        String requestedBy,
        String reason,
        java.time.Instant appliedAt,
        java.time.Instant createdAt
    ) {
    }

    public record RbacRequestListResponse(
        List<RbacRequestItem> items,
        int limit,
        int offset,
        String traceId
    ) {
    }

    public record RbacApprovalActionRequest(
        String comment
    ) {
    }

    public record RbacApprovalActionResponse(
        String status,
        int approvalCount,
        Long permissionVersion,
        String traceId
    ) {
    }
}
