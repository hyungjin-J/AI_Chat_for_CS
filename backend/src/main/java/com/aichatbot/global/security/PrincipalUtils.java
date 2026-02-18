package com.aichatbot.global.security;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.tenant.TenantContext;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

public final class PrincipalUtils {

    private PrincipalUtils() {
    }

    public static UserPrincipal currentPrincipal() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            throw new ApiException(
                HttpStatus.UNAUTHORIZED,
                "SEC-001-401",
                ErrorCatalog.messageOf("SEC-001-401"),
                List.of("authentication_required")
            );
        }

        Object principal = authentication.getPrincipal();
        if (principal instanceof UserPrincipal userPrincipal) {
            return userPrincipal;
        }

        String tenantId = TenantContext.getTenantId();
        String userId = principal == null ? "unknown-user" : String.valueOf(principal);
        List<String> roles = authentication.getAuthorities().stream()
            .map(authority -> authority.getAuthority())
            .map(role -> role.startsWith("ROLE_") ? role.substring(5) : role)
            .collect(Collectors.toList());

        return new UserPrincipal(userId, tenantId, userId, roles);
    }
}
