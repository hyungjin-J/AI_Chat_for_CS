package com.aichatbot.rag.application;

import java.util.UUID;

public record EvidenceChunk(
    UUID chunkId,
    UUID documentId,
    String title,
    int versionNo,
    int rankNo,
    double score,
    String excerptMasked,
    String originalChunkText
) {
}
