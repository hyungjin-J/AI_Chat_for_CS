package com.aichatbot.rag.presentation;

public record RagSafeResponse(
    String responseType,
    String id,
    String message,
    String traceId
) {
}
