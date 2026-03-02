package com.aichatbot.contexts.knowledge.rag.infrastructure;

import com.aichatbot.contexts.knowledge.rag.application.KbAdminPort;
import com.aichatbot.contexts.knowledge.rag.domain.mapper.KbAdminMapper;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentAdminRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentVersionSourceRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Primary;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

@Primary
@Repository
public class KbAdminRepository implements KbAdminPort {

    public static final String JOB_TYPE_DOCUMENT_VERSION = "DOCUMENT_VERSION";
    public static final String JOB_TYPE_REINDEX_ALL = "REINDEX_ALL";
    public static final String JOB_STATUS_PENDING = "PENDING";
    public static final String JOB_STATUS_RUNNING = "RUNNING";
    public static final String JOB_STATUS_RETRY_WAIT = "RETRY_WAIT";
    public static final String JOB_STATUS_DONE = "DONE";
    public static final String JOB_STATUS_DEAD_LETTER = "DEAD_LETTER";
    public static final int DEFAULT_MAX_ATTEMPTS = 3;

    private final KbAdminMapper kbAdminMapper;

    public KbAdminRepository(KbAdminMapper kbAdminMapper) {
        this.kbAdminMapper = kbAdminMapper;
    }

    public KbAdminPort.DocumentCreateResult createDocument(
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
    ) {
        UUID documentId = UUID.randomUUID();
        kbAdminMapper.insertDocument(
            documentId,
            tenantId,
            title,
            sourceType,
            category,
            effectiveDate,
            owner,
            nowUtc
        );

        UUID documentVersionId = UUID.randomUUID();
        kbAdminMapper.insertDocumentVersion(
            documentVersionId,
            tenantId,
            documentId,
            1,
            "pending",
            null,
            rawContentMasked,
            "QUEUED",
            nowUtc,
            nowUtc
        );

        KbReindexJobRow job = createOrGetJobByIdempotency(
            tenantId,
            JOB_TYPE_DOCUMENT_VERSION,
            documentVersionId,
            idempotencyKey,
            "document_index_requested",
            null,
            nowUtc,
            traceId
        );

        return new KbAdminPort.DocumentCreateResult(documentId, documentVersionId, job.id());
    }

    public List<KbDocumentAdminRow> findLatestDocuments(UUID tenantId, String status, int limit, int offset) {
        return kbAdminMapper.findLatestDocuments(tenantId, status, limit, offset);
    }

    public Optional<KbDocumentAdminRow> findDocumentById(UUID tenantId, UUID documentId) {
        return Optional.ofNullable(kbAdminMapper.findDocumentById(tenantId, documentId));
    }

    public Optional<KbDocumentAdminRow> findDocumentVersionByNo(UUID tenantId, UUID documentId, int versionNo) {
        return Optional.ofNullable(kbAdminMapper.findDocumentVersionByNo(tenantId, documentId, versionNo));
    }

    public int approveLatestVersion(UUID tenantId, UUID documentId, Instant nowUtc) {
        Integer latestVersionNo = kbAdminMapper.findLatestVersionNo(tenantId, documentId);
        if (latestVersionNo == null) {
            return 0;
        }
        kbAdminMapper.archiveApprovedVersionsExcept(tenantId, documentId, latestVersionNo, nowUtc);
        return kbAdminMapper.updateDocumentVersionStatus(tenantId, documentId, latestVersionNo, "approved", nowUtc, nowUtc);
    }

    public int rollbackToVersion(UUID tenantId, UUID documentId, int versionNo, Instant nowUtc) {
        kbAdminMapper.archiveApprovedVersionsExcept(tenantId, documentId, versionNo, nowUtc);
        return kbAdminMapper.updateDocumentVersionStatus(tenantId, documentId, versionNo, "approved", nowUtc, nowUtc);
    }

    public KbReindexJobRow createOrGetReindexJob(
        UUID tenantId,
        UUID requestedBy,
        String noteMasked,
        String idempotencyKey,
        UUID traceId,
        Instant nowUtc
    ) {
        return createOrGetJobByIdempotency(
            tenantId,
            JOB_TYPE_REINDEX_ALL,
            null,
            idempotencyKey,
            noteMasked,
            requestedBy,
            nowUtc,
            traceId
        );
    }

    public Optional<KbReindexJobRow> findReindexJobById(UUID tenantId, UUID jobId) {
        return Optional.ofNullable(kbAdminMapper.findReindexJobById(tenantId, jobId));
    }

    public List<KbReindexJobRow> findRecentReindexJobs(UUID tenantId, int limit) {
        return kbAdminMapper.findRecentReindexJobs(tenantId, limit);
    }

    public List<KbReindexJobRow> findPendingIndexJobs(Instant nowUtc, int limit) {
        return kbAdminMapper.findPendingIndexJobs(nowUtc, limit);
    }

    public boolean claimIndexJob(UUID tenantId, UUID jobId, Instant startedAt, UUID traceId) {
        return kbAdminMapper.claimIndexJob(tenantId, jobId, startedAt, traceId) == 1;
    }

    public void markIndexJobDone(UUID tenantId, UUID jobId, Instant completedAt, String resultMessage) {
        kbAdminMapper.markIndexJobDone(tenantId, jobId, completedAt, resultMessage);
    }

    public void markIndexJobRetry(
        UUID tenantId,
        UUID jobId,
        Instant nextRetryAt,
        String errorCode,
        String errorExcerpt,
        Instant completedAt,
        UUID traceId
    ) {
        kbAdminMapper.markIndexJobRetry(
            tenantId,
            jobId,
            nextRetryAt,
            errorCode,
            errorExcerpt,
            completedAt,
            traceId
        );
    }

    public void markIndexJobDeadLetter(
        UUID tenantId,
        UUID jobId,
        String errorCode,
        String errorExcerpt,
        Instant completedAt,
        UUID traceId
    ) {
        kbAdminMapper.markIndexJobDeadLetter(
            tenantId,
            jobId,
            errorCode,
            errorExcerpt,
            completedAt,
            traceId
        );
    }

    public Optional<KbDocumentVersionSourceRow> findDocumentVersionSourceForIndexing(UUID tenantId, UUID documentVersionId) {
        return Optional.ofNullable(kbAdminMapper.findDocumentVersionSourceForIndexing(tenantId, documentVersionId));
    }

    public List<UUID> findApprovedDocumentVersionIds(UUID tenantId) {
        return kbAdminMapper.findApprovedDocumentVersionIds(tenantId);
    }

    public void updateDocumentVersionPipelineState(
        UUID tenantId,
        UUID documentVersionId,
        String pipelineStatus,
        String pipelineErrorCode,
        String pipelineErrorExcerpt,
        Instant updatedAt
    ) {
        kbAdminMapper.updateDocumentVersionPipelineState(
            tenantId,
            documentVersionId,
            pipelineStatus,
            pipelineErrorCode,
            pipelineErrorExcerpt,
            updatedAt
        );
    }

    public void deleteChunksAndEmbeddings(UUID tenantId, UUID documentVersionId) {
        kbAdminMapper.deleteChunkEmbeddingsByDocumentVersion(tenantId, documentVersionId);
        kbAdminMapper.deleteChunksByDocumentVersion(tenantId, documentVersionId);
    }

    public UUID insertChunk(
        UUID tenantId,
        UUID documentVersionId,
        int chunkNo,
        String chunkHash,
        String chunkText,
        int tokenCount,
        String contextHeader,
        String summaryText,
        Instant createdAt
    ) {
        UUID chunkId = UUID.randomUUID();
        kbAdminMapper.insertChunk(
            chunkId,
            tenantId,
            documentVersionId,
            chunkNo,
            chunkHash,
            chunkText,
            tokenCount,
            contextHeader,
            summaryText,
            createdAt
        );
        return chunkId;
    }

    public void insertChunkEmbedding(
        UUID tenantId,
        UUID chunkId,
        String embeddingVector,
        int embeddingDim,
        String model,
        String embeddingInputText,
        Instant createdAt
    ) {
        kbAdminMapper.insertChunkEmbedding(
            UUID.randomUUID(),
            tenantId,
            chunkId,
            embeddingVector,
            embeddingDim,
            model,
            embeddingInputText,
            createdAt
        );
    }

    public int countChunksByDocumentVersion(UUID tenantId, UUID documentVersionId) {
        return kbAdminMapper.countChunksByDocumentVersion(tenantId, documentVersionId);
    }

    private KbReindexJobRow createOrGetJobByIdempotency(
        UUID tenantId,
        String jobType,
        UUID documentVersionId,
        String idempotencyKey,
        String resultMessage,
        UUID requestedBy,
        Instant nowUtc,
        UUID traceId
    ) {
        String normalizedKey = normalizeIdempotencyKey(idempotencyKey);
        if (normalizedKey != null) {
            KbReindexJobRow existing = kbAdminMapper.findReindexJobByIdempotencyKey(tenantId, normalizedKey);
            if (existing != null) {
                return existing;
            }
        }

        UUID jobId = UUID.randomUUID();
        String persistedIdempotencyKey = normalizedKey == null ? "AUTO-" + jobId : normalizedKey;
        try {
            kbAdminMapper.insertReindexJob(
                jobId,
                tenantId,
                jobType,
                documentVersionId,
                persistedIdempotencyKey,
                JOB_STATUS_PENDING,
                0,
                DEFAULT_MAX_ATTEMPTS,
                nowUtc,
                null,
                null,
                requestedBy,
                nowUtc,
                null,
                null,
                resultMessage,
                traceId,
                nowUtc
            );
        } catch (DuplicateKeyException duplicateKeyException) {
            if (normalizedKey != null) {
                KbReindexJobRow existing = kbAdminMapper.findReindexJobByIdempotencyKey(tenantId, normalizedKey);
                if (existing != null) {
                    return existing;
                }
            }
            throw duplicateKeyException;
        }

        return kbAdminMapper.findReindexJobById(tenantId, jobId);
    }

    private String normalizeIdempotencyKey(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        return rawValue.trim();
    }
}
