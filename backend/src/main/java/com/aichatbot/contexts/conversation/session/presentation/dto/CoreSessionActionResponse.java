package com.aichatbot.contexts.conversation.session.presentation.dto;

public record CoreSessionActionResponse(
    String result,
    String action,
    String sessionId,
    String traceId
) {
}
