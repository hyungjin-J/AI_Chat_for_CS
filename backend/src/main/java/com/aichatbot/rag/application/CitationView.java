package com.aichatbot.rag.application;

import java.time.Instant;
import java.util.UUID;

public record CitationView(
    UUID id,
    UUID tenantId,
    UUID messageId,
    UUID chunkId,
    int rankNo,
    String excerptMasked,
    Instant createdAt
) {
}
