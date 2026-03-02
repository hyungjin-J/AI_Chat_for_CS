package com.aichatbot.contexts.conversation.session.presentation.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public record CsatPostRequest(
    @Min(1)
    @Max(5)
    int score,
    String comment
) {
}
