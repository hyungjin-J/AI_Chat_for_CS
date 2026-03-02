package com.aichatbot.contexts.conversation.session.presentation.dto;

import jakarta.validation.constraints.NotBlank;

public record MessageRetryRequest(
    @NotBlank
    String reason
) {
}
