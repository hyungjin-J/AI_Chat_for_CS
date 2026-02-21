package com.aichatbot.global.security;

import java.util.List;

public record UserPrincipal(
    String userId,
    String tenantId,
    String loginId,
    List<String> roles,
    long permissionVersion,
    String adminLevel
) {
    public boolean hasRole(String roleCode) {
        if (roleCode == null || roleCode.isBlank()) {
            return false;
        }
        return roles.stream().anyMatch(value -> roleCode.equalsIgnoreCase(value));
    }
}

