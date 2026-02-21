package com.aichatbot.admin.infrastructure;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RbacApprovalService {

    private final RbacApprovalRepository rbacApprovalRepository;
    private final RbacMatrixService rbacMatrixService;
    private final Clock clock;

    @Autowired
    public RbacApprovalService(RbacApprovalRepository rbacApprovalRepository, RbacMatrixService rbacMatrixService) {
        this(rbacApprovalRepository, rbacMatrixService, Clock.systemUTC());
    }

    RbacApprovalService(RbacApprovalRepository rbacApprovalRepository, RbacMatrixService rbacMatrixService, Clock clock) {
        this.rbacApprovalRepository = rbacApprovalRepository;
        this.rbacMatrixService = rbacMatrixService;
        this.clock = clock;
    }

    @Transactional
    public UUID createRequest(
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        UUID requestedBy,
        String reason
    ) {
        return rbacApprovalRepository.createRequest(
            tenantId,
            normalize(resourceKey),
            normalize(roleCode),
            normalize(adminLevel),
            allowed,
            requestedBy,
            reason,
            Instant.now(clock)
        );
    }

    public List<RbacChangeRequestRecord> listRequests(UUID tenantId, String status, int limit, int offset) {
        return rbacApprovalRepository.listRequests(tenantId, status == null ? null : normalize(status), limit, offset);
    }

    @Transactional(noRollbackFor = ApiException.class)
    public ApprovalResult approve(UUID tenantId, UUID requestId, UUID approverUserId, String approverAdminLevel, String comment) {
        if (!"SYSTEM_ADMIN".equalsIgnoreCase(approverAdminLevel)) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                ErrorCatalog.messageOf("SEC-002-403"),
                List.of("approval_requires_system_admin")
            );
        }

        RbacChangeRequestRecord request = rbacApprovalRepository.findRequest(tenantId, requestId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", ErrorCatalog.messageOf("API-004-404"), List.of("request_not_found")));
        if (!"PENDING".equalsIgnoreCase(request.status())) {
            throw new ApiException(HttpStatus.CONFLICT, "RBAC_APPROVAL_INVALID", ErrorCatalog.messageOf("RBAC_APPROVAL_INVALID"), List.of("request_not_pending"));
        }
        if (request.requestedBy().equals(approverUserId)) {
            throw new ApiException(HttpStatus.CONFLICT, "RBAC_APPROVAL_INVALID", ErrorCatalog.messageOf("RBAC_APPROVAL_INVALID"), List.of("self_approval_not_allowed"));
        }
        if (!rbacApprovalRepository.addApproval(requestId, tenantId, approverUserId, "APPROVE", comment, Instant.now(clock))) {
            throw new ApiException(HttpStatus.CONFLICT, "RBAC_APPROVAL_INVALID", ErrorCatalog.messageOf("RBAC_APPROVAL_INVALID"), List.of("duplicated_approver"));
        }

        int approvalCount = rbacApprovalRepository.countApprovals(requestId, "APPROVE");
        if (approvalCount < 2) {
            return new ApprovalResult("PENDING", approvalCount, null);
        }

        long permissionVersion = rbacMatrixService.upsertAndBumpPermissionVersion(
            tenantId,
            request.resourceKey(),
            request.roleCode(),
            request.adminLevel(),
            request.allowed(),
            approverUserId
        );
        rbacApprovalRepository.updateRequestStatus(tenantId, requestId, "APPROVED", Instant.now(clock), Instant.now(clock));
        return new ApprovalResult("APPLIED", approvalCount, permissionVersion);
    }

    @Transactional
    public void reject(UUID tenantId, UUID requestId, UUID approverUserId, String approverAdminLevel, String comment) {
        if (!"SYSTEM_ADMIN".equalsIgnoreCase(approverAdminLevel)) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                ErrorCatalog.messageOf("SEC-002-403"),
                List.of("approval_requires_system_admin")
            );
        }
        RbacChangeRequestRecord request = rbacApprovalRepository.findRequest(tenantId, requestId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "API-004-404", ErrorCatalog.messageOf("API-004-404"), List.of("request_not_found")));
        if (!"PENDING".equalsIgnoreCase(request.status())) {
            throw new ApiException(HttpStatus.CONFLICT, "RBAC_APPROVAL_INVALID", ErrorCatalog.messageOf("RBAC_APPROVAL_INVALID"), List.of("request_not_pending"));
        }
        rbacApprovalRepository.addApproval(requestId, tenantId, approverUserId, "REJECT", comment, Instant.now(clock));
        rbacApprovalRepository.updateRequestStatus(tenantId, requestId, "REJECTED", null, Instant.now(clock));
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
    }

    public record ApprovalResult(
        String status,
        int approvalCount,
        Long permissionVersion
    ) {
    }
}
