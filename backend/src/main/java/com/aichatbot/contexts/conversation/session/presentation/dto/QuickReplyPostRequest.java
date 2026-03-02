package com.aichatbot.contexts.conversation.session.presentation.dto;

import jakarta.validation.constraints.NotBlank;

public record QuickReplyPostRequest(
    @NotBlank
    String text
) {
}
