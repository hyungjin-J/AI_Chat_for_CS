package com.aichatbot.contexts.knowledge.rag.application;

import java.util.List;

public record RetrievalResult(
    List<EvidenceChunk> evidenceChunks,
    String retrievalMode,
    double evidenceScore,
    boolean zeroEvidence
) {
}

