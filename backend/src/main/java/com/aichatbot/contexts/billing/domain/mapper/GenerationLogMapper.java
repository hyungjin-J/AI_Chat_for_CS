package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.GenerationLogRow;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface GenerationLogMapper {

    int insert(@Param("generationLogKey") String generationLogKey,
               @Param("tenantKey") String tenantKey,
               @Param("messageKey") String messageKey,
               @Param("providerCode") String providerCode,
               @Param("modelCode") String modelCode,
               @Param("inputTokens") int inputTokens,
               @Param("outputTokens") int outputTokens,
               @Param("toolCalls") int toolCalls,
               @Param("promptMasked") String promptMasked,
               @Param("traceToken") String traceToken,
               @Param("createdAt") Instant createdAt);

    List<GenerationLogRow> findByTenant(@Param("tenantKey") String tenantKey);

    List<GenerationLogRow> findByTenantAndDate(@Param("tenantKey") String tenantKey, @Param("usageDate") LocalDate usageDate);

    List<GenerationLogRow> findByTenantAndMonth(@Param("tenantKey") String tenantKey,
                                                @Param("monthFrom") LocalDate monthFrom,
                                                @Param("monthTo") LocalDate monthTo);

    List<GenerationLogRow> findByDate(@Param("usageDate") LocalDate usageDate);

    List<GenerationLogRow> findAll();

    int deleteAll();
}
