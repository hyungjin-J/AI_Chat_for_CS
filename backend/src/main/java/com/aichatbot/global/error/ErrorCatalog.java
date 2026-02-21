package com.aichatbot.global.error;

import java.util.Map;

public final class ErrorCatalog {

    private static final Map<String, String> MESSAGES = Map.ofEntries(
        Map.entry("SEC-001-401", "Authentication is required or token is expired."),
        Map.entry("SEC-002-403", "You do not have permission to access this resource."),
        Map.entry("SYS-002-403", "Tenant scope is invalid."),
        Map.entry("API-003-409", "A duplicate request is already in progress or completed."),
        Map.entry("API-003-422", "Request payload is invalid."),
        Map.entry("API-004-404", "Requested resource was not found."),
        Map.entry("API-008-429-BUDGET", "Request budget exceeded. Retry later."),
        Map.entry("API-008-429-SSE", "Concurrent SSE stream limit exceeded."),
        Map.entry("AI-009-422-SCHEMA", "Answer contract schema validation failed."),
        Map.entry("AI-009-409-CITATION", "Citations are required but missing."),
        Map.entry("AI-009-409-EVIDENCE", "Evidence score is below required threshold."),
        Map.entry("AI-009-200-SAFE", "Safe response was returned due to policy gate."),
        Map.entry("RAG-002-422-POLICY", "Policy validation blocked the response."),
        Map.entry("SYS-004-409-TRACE", "trace_id is required for this request."),
        Map.entry("SYS-003-500", "Internal server error."),
        Map.entry("SYS-003-503", "Dependent service is temporarily unavailable."),
        Map.entry("AUTH_STALE_PERMISSION", "Permission version changed. Re-authentication required."),
        Map.entry("AUTH_LOCKED", "Account is temporarily locked due to repeated failures."),
        Map.entry("AUTH_RATE_LIMITED", "Too many login attempts. Retry after the current window."),
        Map.entry("AUTH_REFRESH_REUSE_DETECTED", "Refresh token reuse was detected. Session family revoked."),
        Map.entry("AUTH_MFA_INVALID_CODE", "The MFA verification code is invalid."),
        Map.entry("AUTH_MFA_LOCKED", "MFA verification is temporarily locked due to repeated failures."),
        Map.entry("AUTH_MFA_SETUP_REQUIRED", "MFA setup is required before completing authentication."),
        Map.entry("AUTH_MFA_CHALLENGE_INVALID", "MFA challenge is invalid or expired."),
        Map.entry("RBAC_APPROVAL_INVALID", "RBAC approval workflow condition was not satisfied."),
        Map.entry("AUDIT_EXPORT_RANGE_EXCEEDED", "Requested audit export range exceeded allowed limits.")
    );

    private ErrorCatalog() {
    }

    public static String messageOf(String code) {
        return MESSAGES.getOrDefault(code, "Request failed.");
    }
}
