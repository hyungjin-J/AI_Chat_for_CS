package com.aichatbot.session.presentation.dto;

import jakarta.validation.constraints.Size;

public record CreateSessionRequest(
    @Size(max = 120)
    String sessionId,
    @Size(max = 120)
    String reason
) {
}
