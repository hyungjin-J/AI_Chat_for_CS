package com.aichatbot.contexts.knowledge.rag.domain.mapper;

import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentAdminRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbDocumentVersionSourceRow;
import com.aichatbot.contexts.knowledge.rag.domain.model.KbReindexJobRow;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface KbAdminMapper {

    int insertDocument(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("title") String title,
        @Param("sourceType") String sourceType,
        @Param("category") String category,
        @Param("effectiveDate") LocalDate effectiveDate,
        @Param("owner") String owner,
        @Param("createdAt") Instant createdAt
    );

    int insertDocumentVersion(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId,
        @Param("versionNo") int versionNo,
        @Param("status") String status,
        @Param("approvedAt") Instant approvedAt,
        @Param("rawContentMasked") String rawContentMasked,
        @Param("pipelineStatus") String pipelineStatus,
        @Param("pipelineUpdatedAt") Instant pipelineUpdatedAt,
        @Param("createdAt") Instant createdAt
    );

    Integer findLatestVersionNo(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId
    );

    UUID findLatestDocumentVersionId(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId
    );

    List<KbDocumentAdminRow> findLatestDocuments(
        @Param("tenantId") UUID tenantId,
        @Param("status") String status,
        @Param("limit") int limit,
        @Param("offset") int offset
    );

    KbDocumentAdminRow findDocumentById(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId
    );

    KbDocumentAdminRow findDocumentVersionByNo(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId,
        @Param("versionNo") int versionNo
    );

    KbDocumentVersionSourceRow findDocumentVersionSourceForIndexing(
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId
    );

    List<UUID> findApprovedDocumentVersionIds(@Param("tenantId") UUID tenantId);

    int updateDocumentVersionStatus(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId,
        @Param("versionNo") int versionNo,
        @Param("status") String status,
        @Param("approvedAt") Instant approvedAt,
        @Param("updatedAt") Instant updatedAt
    );

    int updateDocumentVersionPipelineState(
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId,
        @Param("pipelineStatus") String pipelineStatus,
        @Param("pipelineErrorCode") String pipelineErrorCode,
        @Param("pipelineErrorExcerpt") String pipelineErrorExcerpt,
        @Param("updatedAt") Instant updatedAt
    );

    int archiveApprovedVersionsExcept(
        @Param("tenantId") UUID tenantId,
        @Param("documentId") UUID documentId,
        @Param("versionNo") int versionNo,
        @Param("updatedAt") Instant updatedAt
    );

    int deleteChunkEmbeddingsByDocumentVersion(
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId
    );

    int deleteChunksByDocumentVersion(
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId
    );

    int insertChunk(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId,
        @Param("chunkNo") int chunkNo,
        @Param("chunkHash") String chunkHash,
        @Param("chunkText") String chunkText,
        @Param("tokenCount") int tokenCount,
        @Param("contextHeader") String contextHeader,
        @Param("summaryText") String summaryText,
        @Param("createdAt") Instant createdAt
    );

    int insertChunkEmbedding(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("chunkId") UUID chunkId,
        @Param("embeddingVector") String embeddingVector,
        @Param("embeddingDim") int embeddingDim,
        @Param("model") String model,
        @Param("embeddingInputText") String embeddingInputText,
        @Param("createdAt") Instant createdAt
    );

    int countChunksByDocumentVersion(
        @Param("tenantId") UUID tenantId,
        @Param("documentVersionId") UUID documentVersionId
    );

    int insertReindexJob(
        @Param("id") UUID id,
        @Param("tenantId") UUID tenantId,
        @Param("jobType") String jobType,
        @Param("documentVersionId") UUID documentVersionId,
        @Param("idempotencyKey") String idempotencyKey,
        @Param("status") String status,
        @Param("attemptCount") int attemptCount,
        @Param("maxAttempts") int maxAttempts,
        @Param("nextRetryAt") Instant nextRetryAt,
        @Param("errorCode") String errorCode,
        @Param("errorExcerpt") String errorExcerpt,
        @Param("requestedBy") UUID requestedBy,
        @Param("requestedAt") Instant requestedAt,
        @Param("startedAt") Instant startedAt,
        @Param("completedAt") Instant completedAt,
        @Param("resultMessage") String resultMessage,
        @Param("lastTraceId") UUID lastTraceId,
        @Param("updatedAt") Instant updatedAt
    );

    KbReindexJobRow findReindexJobById(
        @Param("tenantId") UUID tenantId,
        @Param("jobId") UUID jobId
    );

    KbReindexJobRow findReindexJobByIdempotencyKey(
        @Param("tenantId") UUID tenantId,
        @Param("idempotencyKey") String idempotencyKey
    );

    List<KbReindexJobRow> findRecentReindexJobs(
        @Param("tenantId") UUID tenantId,
        @Param("limit") int limit
    );

    List<KbReindexJobRow> findPendingIndexJobs(
        @Param("nowUtc") Instant nowUtc,
        @Param("limit") int limit
    );

    int claimIndexJob(
        @Param("tenantId") UUID tenantId,
        @Param("jobId") UUID jobId,
        @Param("startedAt") Instant startedAt,
        @Param("traceId") UUID traceId
    );

    int markIndexJobDone(
        @Param("tenantId") UUID tenantId,
        @Param("jobId") UUID jobId,
        @Param("completedAt") Instant completedAt,
        @Param("resultMessage") String resultMessage
    );

    int markIndexJobRetry(
        @Param("tenantId") UUID tenantId,
        @Param("jobId") UUID jobId,
        @Param("nextRetryAt") Instant nextRetryAt,
        @Param("errorCode") String errorCode,
        @Param("errorExcerpt") String errorExcerpt,
        @Param("completedAt") Instant completedAt,
        @Param("traceId") UUID traceId
    );

    int markIndexJobDeadLetter(
        @Param("tenantId") UUID tenantId,
        @Param("jobId") UUID jobId,
        @Param("errorCode") String errorCode,
        @Param("errorExcerpt") String errorExcerpt,
        @Param("completedAt") Instant completedAt,
        @Param("traceId") UUID traceId
    );
}
