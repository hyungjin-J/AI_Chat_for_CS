package com.aichatbot.global.tenant.domain.mapper;

import org.apache.ibatis.annotations.Param;

public interface TenantResolverMapper {

    String findTenantIdByKey(@Param("tenantKey") String tenantKey);
}
