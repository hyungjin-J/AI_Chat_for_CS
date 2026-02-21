package com.aichatbot.auth.presentation.dto;

import jakarta.validation.constraints.Size;

public record LogoutRequest(
    @Size(max = 4096)
    String refreshToken,
    @Size(max = 60)
    String clientType,
    @Size(max = 120)
    String clientNonce,
    @Size(max = 200)
    String reason
) {
}

