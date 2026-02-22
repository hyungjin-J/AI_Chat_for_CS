package com.aichatbot.contexts.operations.audit.domain;

import java.time.Instant;
import java.util.UUID;

public record AuditExportChunkRecord(
    UUID jobId,
    Integer chunkNo,
    byte[] payloadBytes,
    String payloadHash,
    Instant createdAt
) {
}

