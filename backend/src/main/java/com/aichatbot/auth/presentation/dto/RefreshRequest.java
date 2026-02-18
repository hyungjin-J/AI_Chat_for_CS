package com.aichatbot.auth.presentation.dto;

import jakarta.validation.constraints.NotBlank;

public record RefreshRequest(
    @NotBlank
    String refreshToken,
    String clientNonce
) {
}
