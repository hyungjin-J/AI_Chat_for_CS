package com.aichatbot.auth.presentation.dto;

import java.util.List;

public record AuthTokenResponse(
    String result,
    String accessToken,
    String refreshToken,
    String sessionFamilyId,
    String mfaTicketId,
    String mfaStatus,
    String userId,
    String tenantId,
    List<String> roles,
    long permissionVersion,
    String adminLevel,
    List<String> recoveryCodes,
    String traceId
) {
}
