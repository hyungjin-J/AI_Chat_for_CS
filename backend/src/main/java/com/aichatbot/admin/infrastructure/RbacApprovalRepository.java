package com.aichatbot.admin.infrastructure;

import com.aichatbot.admin.domain.mapper.RbacApprovalMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Repository
public class RbacApprovalRepository {

    private final RbacApprovalMapper rbacApprovalMapper;

    public RbacApprovalRepository(RbacApprovalMapper rbacApprovalMapper) {
        this.rbacApprovalMapper = rbacApprovalMapper;
    }

    public UUID createRequest(
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        UUID requestedBy,
        String reason,
        Instant createdAt
    ) {
        UUID requestId = UUID.randomUUID();
        rbacApprovalMapper.insertChangeRequest(
            requestId,
            tenantId,
            resourceKey,
            roleCode,
            adminLevel,
            allowed,
            requestedBy,
            reason,
            "PENDING",
            createdAt
        );
        return requestId;
    }

    public Optional<RbacChangeRequestRecord> findRequest(UUID tenantId, UUID requestId) {
        return Optional.ofNullable(rbacApprovalMapper.findChangeRequestById(tenantId, requestId));
    }

    public List<RbacChangeRequestRecord> listRequests(UUID tenantId, String status, int limit, int offset) {
        return rbacApprovalMapper.listChangeRequests(tenantId, status, limit, offset);
    }

    public boolean addApproval(UUID requestId, UUID tenantId, UUID approverUserId, String decision, String comment, Instant decidedAt) {
        try {
            return rbacApprovalMapper.insertApproval(UUID.randomUUID(), requestId, tenantId, approverUserId, decision, comment, decidedAt) == 1;
        } catch (DuplicateKeyException duplicateKeyException) {
            return false;
        }
    }

    public int countApprovals(UUID requestId, String decision) {
        return rbacApprovalMapper.countApprovals(requestId, decision);
    }

    public int updateRequestStatus(UUID tenantId, UUID requestId, String status, Instant appliedAt, Instant updatedAt) {
        return rbacApprovalMapper.updateChangeRequestStatus(tenantId, requestId, status, appliedAt, updatedAt);
    }
}
