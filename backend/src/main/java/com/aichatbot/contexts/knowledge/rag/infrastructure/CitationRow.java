package com.aichatbot.contexts.knowledge.rag.infrastructure;

import java.time.Instant;

public record CitationRow(
    String id,
    String tenantId,
    String messageId,
    String chunkId,
    int rankNo,
    String excerptMasked,
    Instant createdAt
) {
}

