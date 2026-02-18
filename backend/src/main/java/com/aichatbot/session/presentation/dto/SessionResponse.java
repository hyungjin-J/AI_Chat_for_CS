package com.aichatbot.session.presentation.dto;

public record SessionResponse(
    String result,
    String sessionId,
    String status,
    String traceId
) {
}
