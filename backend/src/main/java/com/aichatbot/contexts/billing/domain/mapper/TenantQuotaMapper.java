package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.readmodel.TenantQuotaRow;
import java.time.Instant;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface TenantQuotaMapper {

    int deleteByTenantAndEffectiveFrom(@Param("tenantKey") String tenantKey, @Param("effectiveFrom") Instant effectiveFrom);

    int insert(@Param("tenantKey") String tenantKey,
               @Param("maxQps") int maxQps,
               @Param("maxDailyTokens") long maxDailyTokens,
               @Param("maxMonthlyCost") java.math.BigDecimal maxMonthlyCost,
               @Param("effectiveFrom") Instant effectiveFrom,
               @Param("effectiveTo") Instant effectiveTo,
               @Param("breachAction") String breachAction,
               @Param("updatedBy") String updatedBy,
               @Param("traceToken") String traceToken,
               @Param("updatedAt") Instant updatedAt);

    TenantQuotaRow findActive(@Param("tenantKey") String tenantKey, @Param("at") Instant at);

    TenantQuotaRow findLatest(@Param("tenantKey") String tenantKey);

    List<TenantQuotaRow> findAll(@Param("tenantKey") String tenantKey);

    int deleteAll();
}
