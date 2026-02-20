package com.aichatbot.rag.application;

import java.util.Map;
import java.util.UUID;

public record RagRetrievalRequest(
    UUID tenantId,
    UUID conversationId,
    String queryMasked,
    int topK,
    Map<String, String> filters,
    String traceId
) {
}
