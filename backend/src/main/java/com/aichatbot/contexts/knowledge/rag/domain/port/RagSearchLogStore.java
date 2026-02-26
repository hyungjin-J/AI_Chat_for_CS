package com.aichatbot.contexts.knowledge.rag.domain.port;

import java.util.UUID;

public interface RagSearchLogStore {

    void save(UUID tenantId, UUID conversationId, String queryTextMasked, int topK, String traceId, String retrievalMode);

    String findLatestMaskedQueryByConversation(UUID tenantId, UUID conversationId);

    String findLatestTraceIdByConversation(UUID tenantId, UUID conversationId);
}
