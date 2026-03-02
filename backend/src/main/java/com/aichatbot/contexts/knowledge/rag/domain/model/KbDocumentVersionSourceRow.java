package com.aichatbot.contexts.knowledge.rag.domain.model;

import java.time.LocalDate;
import java.util.UUID;

public record KbDocumentVersionSourceRow(
    UUID tenantId,
    UUID documentId,
    UUID documentVersionId,
    Integer versionNo,
    String title,
    String sourceType,
    String category,
    LocalDate effectiveDate,
    String owner,
    String rawContentMasked
) {
}
