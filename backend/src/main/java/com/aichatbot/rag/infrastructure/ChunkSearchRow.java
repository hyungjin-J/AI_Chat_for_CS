package com.aichatbot.rag.infrastructure;

public record ChunkSearchRow(
    String chunkId,
    String documentId,
    String documentVersionId,
    Integer versionNo,
    Integer chunkNo,
    String title,
    String sourceType,
    String category,
    String effectiveDate,
    String owner,
    String contextHeader,
    String summaryText,
    String chunkText,
    String embeddingInputText
) {
}
