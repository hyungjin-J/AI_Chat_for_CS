package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.TenantSubscription;
import java.time.Instant;
import org.apache.ibatis.annotations.Param;

public interface TenantSubscriptionMapper {

    int deleteByTenant(@Param("tenantKey") String tenantKey);

    int insert(@Param("tenantKey") String tenantKey,
               @Param("planCode") String planCode,
               @Param("status") String status,
               @Param("startedAt") Instant startedAt,
               @Param("endedAt") Instant endedAt);

    TenantSubscription findActive(@Param("tenantKey") String tenantKey, @Param("at") Instant at);

    TenantSubscription findLatest(@Param("tenantKey") String tenantKey);

    int deleteAll();
}
