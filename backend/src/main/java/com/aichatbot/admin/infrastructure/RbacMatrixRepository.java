package com.aichatbot.admin.infrastructure;

import com.aichatbot.admin.domain.mapper.RbacMatrixMapper;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Repository
public class RbacMatrixRepository {

    private final RbacMatrixMapper rbacMatrixMapper;

    public RbacMatrixRepository(RbacMatrixMapper rbacMatrixMapper) {
        this.rbacMatrixMapper = rbacMatrixMapper;
    }

    public void upsert(
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        long permissionVersion,
        UUID updatedBy,
        Instant updatedAt
    ) {
        int updated = rbacMatrixMapper.updateMatrix(
            tenantId,
            resourceKey,
            roleCode,
            adminLevel,
            allowed,
            permissionVersion,
            updatedBy,
            updatedAt
        );
        if (updated > 0) {
            return;
        }
        try {
            rbacMatrixMapper.insertMatrix(
                UUID.randomUUID(),
                tenantId,
                resourceKey,
                roleCode,
                adminLevel,
                allowed,
                permissionVersion,
                updatedBy,
                updatedAt
            );
        } catch (DuplicateKeyException duplicateKeyException) {
            rbacMatrixMapper.updateMatrix(
                tenantId,
                resourceKey,
                roleCode,
                adminLevel,
                allowed,
                permissionVersion,
                updatedBy,
                updatedAt
            );
        }
    }

    public Optional<RbacMatrixEntry> findOne(UUID tenantId, String resourceKey, String roleCode, String adminLevel) {
        return Optional.ofNullable(rbacMatrixMapper.findOne(tenantId, resourceKey, roleCode, adminLevel));
    }
}

