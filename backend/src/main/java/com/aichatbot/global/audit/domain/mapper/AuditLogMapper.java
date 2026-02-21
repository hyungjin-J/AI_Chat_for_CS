package com.aichatbot.global.audit.domain.mapper;

import com.aichatbot.global.audit.domain.AuditChainState;
import com.aichatbot.global.audit.domain.AuditExportChunkRecord;
import com.aichatbot.global.audit.domain.AuditExportJobRecord;
import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface AuditLogMapper {

    int insert(@Param("id") UUID id,
               @Param("tenantId") UUID tenantId,
               @Param("traceId") UUID traceId,
               @Param("actionType") String actionType,
               @Param("actorUserId") UUID actorUserId,
               @Param("actorRole") String actorRole,
               @Param("targetType") String targetType,
               @Param("targetRef") String targetRef,
               @Param("beforeJson") String beforeJson,
               @Param("afterJson") String afterJson,
               @Param("chainSeq") Long chainSeq,
               @Param("hashPrev") String hashPrev,
               @Param("hashCurr") String hashCurr,
               @Param("hashAlgo") String hashAlgo,
               @Param("createdAt") Instant createdAt);

    List<PersistentAuditLogEntry> search(@Param("tenantId") UUID tenantId,
                                         @Param("fromUtc") Instant fromUtc,
                                         @Param("toUtc") Instant toUtc,
                                         @Param("actorUserId") UUID actorUserId,
                                         @Param("actionType") String actionType,
                                         @Param("traceId") UUID traceId,
                                         @Param("limit") int limit,
                                         @Param("offset") int offset);

    PersistentAuditLogEntry findById(@Param("auditId") UUID auditId);

    AuditChainState lockChainState(@Param("tenantId") UUID tenantId);

    int insertChainState(@Param("tenantId") UUID tenantId,
                         @Param("lastSeq") long lastSeq,
                         @Param("lastHash") String lastHash,
                         @Param("updatedAt") Instant updatedAt);

    int updateChainState(@Param("tenantId") UUID tenantId,
                         @Param("lastSeq") long lastSeq,
                         @Param("lastHash") String lastHash,
                         @Param("updatedAt") Instant updatedAt);

    int insertExportLog(@Param("id") UUID id,
                        @Param("tenantId") UUID tenantId,
                        @Param("requestedBy") UUID requestedBy,
                        @Param("format") String format,
                        @Param("fromUtc") Instant fromUtc,
                        @Param("toUtc") Instant toUtc,
                        @Param("rowCount") int rowCount,
                        @Param("traceId") UUID traceId);

    int insertExportJob(@Param("id") UUID id,
                        @Param("tenantId") UUID tenantId,
                        @Param("requestedBy") UUID requestedBy,
                        @Param("status") String status,
                        @Param("exportFormat") String exportFormat,
                        @Param("fromUtc") Instant fromUtc,
                        @Param("toUtc") Instant toUtc,
                        @Param("rowLimit") int rowLimit,
                        @Param("maxBytes") int maxBytes,
                        @Param("maxDurationSec") int maxDurationSec,
                        @Param("expiresAt") Instant expiresAt,
                        @Param("traceId") UUID traceId,
                        @Param("createdAt") Instant createdAt);

    AuditExportJobRecord findExportJobById(@Param("tenantId") UUID tenantId,
                                           @Param("jobId") UUID jobId);

    AuditExportJobRecord findExportJobByIdAnyTenant(@Param("jobId") UUID jobId);

    List<AuditExportJobRecord> findPendingExportJobs(@Param("nowUtc") Instant nowUtc,
                                                     @Param("limit") int limit);

    int claimExportJob(@Param("jobId") UUID jobId,
                       @Param("startedAt") Instant startedAt);

    int markExportJobDone(@Param("jobId") UUID jobId,
                          @Param("rowCount") int rowCount,
                          @Param("totalBytes") int totalBytes,
                          @Param("completedAt") Instant completedAt);

    int markExportJobFailed(@Param("jobId") UUID jobId,
                            @Param("errorCode") String errorCode,
                            @Param("errorMessage") String errorMessage,
                            @Param("completedAt") Instant completedAt);

    List<AuditExportJobRecord> findJobsToExpire(@Param("nowUtc") Instant nowUtc,
                                                @Param("limit") int limit);

    int markExportJobExpired(@Param("jobId") UUID jobId,
                             @Param("completedAt") Instant completedAt);

    int insertExportChunk(@Param("jobId") UUID jobId,
                          @Param("chunkNo") int chunkNo,
                          @Param("payloadBytes") byte[] payloadBytes,
                          @Param("payloadHash") String payloadHash,
                          @Param("createdAt") Instant createdAt);

    List<AuditExportChunkRecord> findExportChunks(@Param("jobId") UUID jobId);

    int deleteExportChunks(@Param("jobId") UUID jobId);
}
