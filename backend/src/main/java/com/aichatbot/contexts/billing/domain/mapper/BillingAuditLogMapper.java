package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.AuditLogEntry;
import java.time.Instant;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface BillingAuditLogMapper {

    int insert(@Param("auditLogKey") String auditLogKey,
               @Param("tenantKey") String tenantKey,
               @Param("actorUserKey") String actorUserKey,
               @Param("actorRole") String actorRole,
               @Param("actionType") String actionType,
               @Param("targetType") String targetType,
               @Param("targetKey") String targetKey,
               @Param("traceToken") String traceToken,
               @Param("beforeJson") String beforeJson,
               @Param("afterJson") String afterJson,
               @Param("createdAt") Instant createdAt);

    List<AuditLogEntry> findByTenant(@Param("tenantKey") String tenantKey);

    List<AuditLogEntry> findAll();

    int deleteAll();
}
