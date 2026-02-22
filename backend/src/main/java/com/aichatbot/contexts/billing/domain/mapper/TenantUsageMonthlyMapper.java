package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.infrastructure.TenantMonthlyUsageRow;
import java.time.LocalDate;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface TenantUsageMonthlyMapper {

    int deleteByTenantAndMonth(@Param("tenantKey") String tenantKey, @Param("usageMonthDate") LocalDate usageMonthDate);

    int insert(@Param("tenantKey") String tenantKey,
               @Param("usageMonthDate") LocalDate usageMonthDate,
               @Param("requestCount") long requestCount,
               @Param("inputTokens") long inputTokens,
               @Param("outputTokens") long outputTokens,
               @Param("toolCalls") long toolCalls,
               @Param("estimatedCost") java.math.BigDecimal estimatedCost,
               @Param("traceToken") String traceToken,
               @Param("updatedAt") java.time.Instant updatedAt);

    TenantMonthlyUsageRow findOne(@Param("tenantKey") String tenantKey, @Param("usageMonthDate") LocalDate usageMonthDate);

    List<TenantMonthlyUsageRow> findByTenantAndMonthRange(@Param("tenantKey") String tenantKey,
                                                           @Param("fromMonthDate") LocalDate fromMonthDate,
                                                           @Param("toMonthDate") LocalDate toMonthDate);

    List<TenantMonthlyUsageRow> findAll();

    int deleteAll();
}
