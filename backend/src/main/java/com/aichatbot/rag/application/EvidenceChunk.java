package com.aichatbot.rag.application;

import java.util.UUID;

public record EvidenceChunk(
    UUID chunkId,
    String chunkTextMasked,
    int rankNo,
    double score
) {
}
