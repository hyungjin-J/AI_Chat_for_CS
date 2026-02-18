package com.aichatbot.auth.domain;

import java.util.List;
import java.util.UUID;

public record AuthUser(
    UUID userId,
    UUID tenantId,
    String tenantKey,
    String loginId,
    String displayName,
    List<String> roles
) {
}
