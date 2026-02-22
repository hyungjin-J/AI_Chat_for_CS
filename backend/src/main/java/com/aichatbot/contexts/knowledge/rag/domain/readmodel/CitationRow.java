package com.aichatbot.contexts.knowledge.rag.domain.readmodel;

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

