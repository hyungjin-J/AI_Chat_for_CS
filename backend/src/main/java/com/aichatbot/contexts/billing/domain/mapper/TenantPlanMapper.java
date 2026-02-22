package com.aichatbot.contexts.billing.domain.mapper;

import com.aichatbot.contexts.billing.domain.model.TenantPlan;
import org.apache.ibatis.annotations.Param;

public interface TenantPlanMapper {

    int deleteByCode(@Param("planCode") String planCode);

    int insert(@Param("planCode") String planCode,
               @Param("name") String name,
               @Param("description") String description);

    TenantPlan findByCode(@Param("planCode") String planCode);

    int deleteAll();
}
