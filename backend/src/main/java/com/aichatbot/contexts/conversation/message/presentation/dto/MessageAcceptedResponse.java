package com.aichatbot.contexts.conversation.message.presentation.dto;

public record MessageAcceptedResponse(
    String result,
    String id,
    String sessionId,
    String traceId
) {
}

