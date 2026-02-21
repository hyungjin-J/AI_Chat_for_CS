package com.aichatbot.admin.domain.mapper;

import com.aichatbot.admin.infrastructure.RbacMatrixEntry;
import java.time.Instant;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface RbacMatrixMapper {

    int updateMatrix(@Param("tenantId") UUID tenantId,
                     @Param("resourceKey") String resourceKey,
                     @Param("roleCode") String roleCode,
                     @Param("adminLevel") String adminLevel,
                     @Param("allowed") boolean allowed,
                     @Param("permissionVersion") long permissionVersion,
                     @Param("updatedBy") UUID updatedBy,
                     @Param("updatedAt") Instant updatedAt);

    int insertMatrix(@Param("id") UUID id,
                     @Param("tenantId") UUID tenantId,
                     @Param("resourceKey") String resourceKey,
                     @Param("roleCode") String roleCode,
                     @Param("adminLevel") String adminLevel,
                     @Param("allowed") boolean allowed,
                     @Param("permissionVersion") long permissionVersion,
                     @Param("updatedBy") UUID updatedBy,
                     @Param("updatedAt") Instant updatedAt);

    RbacMatrixEntry findOne(@Param("tenantId") UUID tenantId,
                            @Param("resourceKey") String resourceKey,
                            @Param("roleCode") String roleCode,
                            @Param("adminLevel") String adminLevel);
}

