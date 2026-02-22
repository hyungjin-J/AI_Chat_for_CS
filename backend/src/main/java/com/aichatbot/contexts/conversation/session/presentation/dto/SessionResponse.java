package com.aichatbot.contexts.conversation.session.presentation.dto;

public record SessionResponse(
    String result,
    String sessionId,
    String status,
    String traceId
) {
}

