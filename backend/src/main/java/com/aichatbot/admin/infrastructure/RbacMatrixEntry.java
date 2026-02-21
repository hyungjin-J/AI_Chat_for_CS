package com.aichatbot.admin.infrastructure;

import java.time.Instant;
import java.util.UUID;

public class RbacMatrixEntry {
    private UUID id;
    private UUID tenantId;
    private String resourceKey;
    private String roleCode;
    private String adminLevel;
    private boolean allowed;
    private long permissionVersion;
    private UUID updatedBy;
    private Instant updatedAt;

    public RbacMatrixEntry() {
    }

    public RbacMatrixEntry(
        UUID id,
        UUID tenantId,
        String resourceKey,
        String roleCode,
        String adminLevel,
        boolean allowed,
        long permissionVersion,
        UUID updatedBy,
        Instant updatedAt
    ) {
        this.id = id;
        this.tenantId = tenantId;
        this.resourceKey = resourceKey;
        this.roleCode = roleCode;
        this.adminLevel = adminLevel;
        this.allowed = allowed;
        this.permissionVersion = permissionVersion;
        this.updatedBy = updatedBy;
        this.updatedAt = updatedAt;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getTenantId() {
        return tenantId;
    }

    public void setTenantId(UUID tenantId) {
        this.tenantId = tenantId;
    }

    public String getResourceKey() {
        return resourceKey;
    }

    public void setResourceKey(String resourceKey) {
        this.resourceKey = resourceKey;
    }

    public String getRoleCode() {
        return roleCode;
    }

    public void setRoleCode(String roleCode) {
        this.roleCode = roleCode;
    }

    public String getAdminLevel() {
        return adminLevel;
    }

    public void setAdminLevel(String adminLevel) {
        this.adminLevel = adminLevel;
    }

    public boolean isAllowed() {
        return allowed;
    }

    public void setAllowed(boolean allowed) {
        this.allowed = allowed;
    }

    public long getPermissionVersion() {
        return permissionVersion;
    }

    public void setPermissionVersion(long permissionVersion) {
        this.permissionVersion = permissionVersion;
    }

    public UUID getUpdatedBy() {
        return updatedBy;
    }

    public void setUpdatedBy(UUID updatedBy) {
        this.updatedBy = updatedBy;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
