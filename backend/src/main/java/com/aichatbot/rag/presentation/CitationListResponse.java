package com.aichatbot.rag.presentation;

import java.util.List;

public record CitationListResponse(
    String result,
    List<CitationItem> data,
    String nextCursor,
    String traceId
) {
    public record CitationItem(
        String citationId,
        String messageId,
        String chunkId,
        int rankNo,
        String excerptMasked
    ) {
    }
}
