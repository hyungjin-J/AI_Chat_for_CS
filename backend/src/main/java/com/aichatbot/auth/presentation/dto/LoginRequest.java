package com.aichatbot.auth.presentation.dto;

import jakarta.validation.constraints.Size;

public record LoginRequest(
    @Size(max = 120)
    String loginId,
    @Size(max = 120)
    String password,
    @Size(max = 40)
    String channelId,
    @Size(max = 120)
    String customerToken,
    @Size(max = 120)
    String clientNonce
) {
}
