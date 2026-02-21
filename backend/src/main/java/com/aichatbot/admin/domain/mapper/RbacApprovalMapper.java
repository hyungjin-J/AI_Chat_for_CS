package com.aichatbot.admin.domain.mapper;

import com.aichatbot.admin.infrastructure.RbacChangeRequestRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface RbacApprovalMapper {

    int insertChangeRequest(@Param("id") UUID id,
                            @Param("tenantId") UUID tenantId,
                            @Param("resourceKey") String resourceKey,
                            @Param("roleCode") String roleCode,
                            @Param("adminLevel") String adminLevel,
                            @Param("allowed") boolean allowed,
                            @Param("requestedBy") UUID requestedBy,
                            @Param("reason") String reason,
                            @Param("status") String status,
                            @Param("createdAt") Instant createdAt);

    RbacChangeRequestRecord findChangeRequestById(@Param("tenantId") UUID tenantId,
                                                  @Param("requestId") UUID requestId);

    List<RbacChangeRequestRecord> listChangeRequests(@Param("tenantId") UUID tenantId,
                                                     @Param("status") String status,
                                                     @Param("limit") int limit,
                                                     @Param("offset") int offset);

    int insertApproval(@Param("id") UUID id,
                       @Param("requestId") UUID requestId,
                       @Param("tenantId") UUID tenantId,
                       @Param("approverUserId") UUID approverUserId,
                       @Param("decision") String decision,
                       @Param("comment") String comment,
                       @Param("decidedAt") Instant decidedAt);

    int countApprovals(@Param("requestId") UUID requestId,
                       @Param("decision") String decision);

    int updateChangeRequestStatus(@Param("tenantId") UUID tenantId,
                                  @Param("requestId") UUID requestId,
                                  @Param("status") String status,
                                  @Param("appliedAt") Instant appliedAt,
                                  @Param("updatedAt") Instant updatedAt);
}
