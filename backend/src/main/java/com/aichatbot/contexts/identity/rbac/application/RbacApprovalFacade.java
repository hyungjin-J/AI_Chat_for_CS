package com.aichatbot.contexts.identity.rbac.application;

import com.aichatbot.contexts.identity.rbac.infrastructure.RbacApprovalService;
import com.aichatbot.contexts.identity.rbac.infrastructure.RbacChangeRequestRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class RbacApprovalFacade {

    private final RbacApprovalService rbacApprovalService;

    public RbacApprovalFacade(RbacApprovalService rbacApprovalService) {
        this.rbacApprovalService = rbacApprovalService;
    }

    public UUID createRequest(
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        UUID requestedBy,
        String reason
    ) {
        return rbacApprovalService.createRequest(tenantId, resourceKey, roleCode, adminLevel, allowed, requestedBy, reason);
    }

    public List<RbacApprovalRequest> listRequests(UUID tenantId, String status, int limit, int offset) {
        return rbacApprovalService.listRequests(tenantId, status, limit, offset).stream()
            .map(this::toApprovalRequest)
            .toList();
    }

    public RbacApprovalOutcome approve(
        UUID tenantId,
        UUID requestId,
        UUID approverUserId,
        String approverAdminLevel,
        String comment
    ) {
        RbacApprovalService.ApprovalResult result = rbacApprovalService.approve(
            tenantId,
            requestId,
            approverUserId,
            approverAdminLevel,
            comment
        );
        return new RbacApprovalOutcome(result.status(), result.approvalCount(), result.permissionVersion());
    }

    public void reject(
        UUID tenantId,
        UUID requestId,
        UUID approverUserId,
        String approverAdminLevel,
        String comment
    ) {
        rbacApprovalService.reject(tenantId, requestId, approverUserId, approverAdminLevel, comment);
    }

    private RbacApprovalRequest toApprovalRequest(RbacChangeRequestRecord record) {
        return new RbacApprovalRequest(
            record.id(),
            record.tenantId(),
            record.resourceKey(),
            record.roleCode(),
            record.adminLevel(),
            record.allowed(),
            record.status(),
            record.requestedBy(),
            record.reason(),
            record.appliedAt(),
            record.createdAt(),
            record.updatedAt()
        );
    }

    public record RbacApprovalRequest(
        UUID id,
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        Boolean allowed,
        String status,
        UUID requestedBy,
        String reason,
        Instant appliedAt,
        Instant createdAt,
        Instant updatedAt
    ) {
    }

    public record RbacApprovalOutcome(
        String status,
        int approvalCount,
        Long permissionVersion
    ) {
    }
}
