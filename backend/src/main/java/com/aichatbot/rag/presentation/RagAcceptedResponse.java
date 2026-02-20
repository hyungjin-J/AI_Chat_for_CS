package com.aichatbot.rag.presentation;

public record RagAcceptedResponse(
    String result,
    String id,
    String traceId
) {
}
