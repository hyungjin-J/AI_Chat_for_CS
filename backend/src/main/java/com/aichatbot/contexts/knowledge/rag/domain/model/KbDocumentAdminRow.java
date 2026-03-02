package com.aichatbot.contexts.knowledge.rag.domain.model;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

public record KbDocumentAdminRow(
    UUID documentId,
    UUID documentVersionId,
    String title,
    String sourceType,
    String category,
    LocalDate effectiveDate,
    String owner,
    Integer versionNo,
    String status,
    String pipelineStatus,
    String pipelineErrorCode,
    String pipelineErrorExcerpt,
    Instant approvedAt,
    Instant updatedAt
) {
}
