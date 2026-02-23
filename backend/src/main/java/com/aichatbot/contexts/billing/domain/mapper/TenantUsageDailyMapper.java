package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.TenantDailyUsageRow;
import java.time.LocalDate;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface TenantUsageDailyMapper {

    int deleteByTenantAndDate(@Param("tenantKey") String tenantKey, @Param("usageDate") LocalDate usageDate);

    int insert(@Param("tenantKey") String tenantKey,
               @Param("usageDate") LocalDate usageDate,
               @Param("requestCount") long requestCount,
               @Param("inputTokens") long inputTokens,
               @Param("outputTokens") long outputTokens,
               @Param("toolCalls") long toolCalls,
               @Param("estimatedCost") java.math.BigDecimal estimatedCost,
               @Param("traceToken") String traceToken,
               @Param("updatedAt") java.time.Instant updatedAt);

    TenantDailyUsageRow findOne(@Param("tenantKey") String tenantKey, @Param("usageDate") LocalDate usageDate);

    List<TenantDailyUsageRow> findByTenantAndDateRange(@Param("tenantKey") String tenantKey,
                                                        @Param("fromDate") LocalDate fromDate,
                                                        @Param("toDate") LocalDate toDate);

    List<TenantDailyUsageRow> findByMonth(@Param("tenantKey") String tenantKey,
                                          @Param("monthFrom") LocalDate monthFrom,
                                          @Param("monthTo") LocalDate monthTo);

    List<TenantDailyUsageRow> findAll();

    int deleteAll();
}
