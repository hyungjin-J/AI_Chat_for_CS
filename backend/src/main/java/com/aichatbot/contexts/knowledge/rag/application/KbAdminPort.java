package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentAdminRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentVersionSourceRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface KbAdminPort {

    String JOB_TYPE_DOCUMENT_VERSION = "DOCUMENT_VERSION";
    String JOB_TYPE_REINDEX_ALL = "REINDEX_ALL";
    String JOB_STATUS_PENDING = "PENDING";
    String JOB_STATUS_RUNNING = "RUNNING";
    String JOB_STATUS_RETRY_WAIT = "RETRY_WAIT";
    String JOB_STATUS_DONE = "DONE";
    String JOB_STATUS_DEAD_LETTER = "DEAD_LETTER";
    int DEFAULT_MAX_ATTEMPTS = 3;

    DocumentCreateResult createDocument(
        UUID tenantId,
        String title,
        String sourceType,
        String category,
        LocalDate effectiveDate,
        String owner,
        String rawContentMasked,
        String idempotencyKey,
        UUID traceId,
        Instant nowUtc
    );

    List<KbDocumentAdminRow> findLatestDocuments(UUID tenantId, String status, int limit, int offset);

    Optional<KbDocumentAdminRow> findDocumentById(UUID tenantId, UUID documentId);

    Optional<KbDocumentAdminRow> findDocumentVersionByNo(UUID tenantId, UUID documentId, int versionNo);

    int approveLatestVersion(UUID tenantId, UUID documentId, Instant nowUtc);

    int rollbackToVersion(UUID tenantId, UUID documentId, int versionNo, Instant nowUtc);

    KbReindexJobRow createOrGetReindexJob(
        UUID tenantId,
        UUID requestedBy,
        String noteMasked,
        String idempotencyKey,
        UUID traceId,
        Instant nowUtc
    );

    Optional<KbReindexJobRow> findReindexJobById(UUID tenantId, UUID jobId);

    List<KbReindexJobRow> findRecentReindexJobs(UUID tenantId, int limit);

    List<KbReindexJobRow> findPendingIndexJobs(Instant nowUtc, int limit);

    boolean claimIndexJob(UUID tenantId, UUID jobId, Instant startedAt, UUID traceId);

    void markIndexJobDone(UUID tenantId, UUID jobId, Instant completedAt, String resultMessage);

    void markIndexJobRetry(
        UUID tenantId,
        UUID jobId,
        Instant nextRetryAt,
        String errorCode,
        String errorExcerpt,
        Instant completedAt,
        UUID traceId
    );

    void markIndexJobDeadLetter(
        UUID tenantId,
        UUID jobId,
        String errorCode,
        String errorExcerpt,
        Instant completedAt,
        UUID traceId
    );

    Optional<KbDocumentVersionSourceRow> findDocumentVersionSourceForIndexing(UUID tenantId, UUID documentVersionId);

    List<UUID> findApprovedDocumentVersionIds(UUID tenantId);

    void updateDocumentVersionPipelineState(
        UUID tenantId,
        UUID documentVersionId,
        String pipelineStatus,
        String pipelineErrorCode,
        String pipelineErrorExcerpt,
        Instant updatedAt
    );

    void deleteChunksAndEmbeddings(UUID tenantId, UUID documentVersionId);

    UUID insertChunk(
        UUID tenantId,
        UUID documentVersionId,
        int chunkNo,
        String chunkHash,
        String chunkText,
        int tokenCount,
        String contextHeader,
        String summaryText,
        Instant createdAt
    );

    void insertChunkEmbedding(
        UUID tenantId,
        UUID chunkId,
        String embeddingVector,
        int embeddingDim,
        String model,
        String embeddingInputText,
        Instant createdAt
    );

    int countChunksByDocumentVersion(UUID tenantId, UUID documentVersionId);

    record DocumentCreateResult(
        UUID documentId,
        UUID documentVersionId,
        UUID jobId
    ) {
    }
}
