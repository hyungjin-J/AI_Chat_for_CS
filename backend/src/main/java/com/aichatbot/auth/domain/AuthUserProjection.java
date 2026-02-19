package com.aichatbot.auth.domain;

public record AuthUserProjection(
    String userId,
    String tenantId,
    String tenantKey,
    String loginId,
    String displayName
) {
}
