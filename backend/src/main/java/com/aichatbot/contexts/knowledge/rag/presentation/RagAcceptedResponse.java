package com.aichatbot.contexts.knowledge.rag.presentation;

public record RagAcceptedResponse(
    String result,
    String id,
    String traceId
) {
}

