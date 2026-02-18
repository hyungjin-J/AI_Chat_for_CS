package com.aichatbot.auth.presentation.dto;

import jakarta.validation.constraints.NotBlank;

public record LogoutRequest(
    @NotBlank
    String refreshToken,
    String clientNonce
) {
}
