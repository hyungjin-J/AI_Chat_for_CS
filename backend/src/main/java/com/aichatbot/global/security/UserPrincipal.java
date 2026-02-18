package com.aichatbot.global.security;

import java.util.List;

public record UserPrincipal(
    String userId,
    String tenantId,
    String loginId,
    List<String> roles
) {
}
