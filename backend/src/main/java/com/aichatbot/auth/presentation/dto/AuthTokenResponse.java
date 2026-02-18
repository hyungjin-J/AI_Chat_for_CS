package com.aichatbot.auth.presentation.dto;

import java.util.List;

public record AuthTokenResponse(
    String result,
    String accessToken,
    String refreshToken,
    String userId,
    String tenantId,
    List<String> roles,
    String traceId
) {
}
