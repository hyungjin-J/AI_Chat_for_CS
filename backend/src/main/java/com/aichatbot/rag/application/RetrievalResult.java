package com.aichatbot.rag.application;

import java.util.List;

public record RetrievalResult(
    List<EvidenceChunk> evidenceChunks,
    String retrievalMode,
    double evidenceScore,
    boolean zeroEvidence
) {
}
