package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.AuditChainState;
import com.aichatbot.global.audit.domain.AuditExportChunkRecord;
import com.aichatbot.global.audit.domain.AuditExportJobRecord;
import com.aichatbot.global.audit.domain.PersistentAuditLogEntry;
import com.aichatbot.global.audit.domain.mapper.AuditLogMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class PersistentAuditLogRepository {

    private final AuditLogMapper auditLogMapper;

    public PersistentAuditLogRepository(AuditLogMapper auditLogMapper) {
        this.auditLogMapper = auditLogMapper;
    }

    public void insert(PersistentAuditLogEntry entry) {
        auditLogMapper.insert(
            entry.id(),
            entry.tenantId(),
            entry.traceId(),
            entry.actionType(),
            entry.actorUserId(),
            entry.actorRole(),
            entry.targetType(),
            entry.targetId(),
            entry.beforeJson(),
            entry.afterJson(),
            entry.chainSeq(),
            entry.hashPrev(),
            entry.hashCurr(),
            entry.hashAlgo(),
            entry.createdAt()
        );
    }

    public List<PersistentAuditLogEntry> search(
        UUID tenantId,
        Instant fromUtc,
        Instant toUtc,
        UUID actorUserId,
        String actionType,
        UUID traceId,
        int limit,
        int offset
    ) {
        return auditLogMapper.search(tenantId, fromUtc, toUtc, actorUserId, actionType, traceId, limit, offset);
    }

    public Optional<PersistentAuditLogEntry> findById(UUID auditId) {
        return Optional.ofNullable(auditLogMapper.findById(auditId));
    }

    public Optional<AuditChainState> lockChainState(UUID tenantId) {
        return Optional.ofNullable(auditLogMapper.lockChainState(tenantId));
    }

    public void insertChainState(UUID tenantId, long lastSeq, String lastHash, Instant updatedAt) {
        auditLogMapper.insertChainState(tenantId, lastSeq, lastHash, updatedAt);
    }

    public void updateChainState(UUID tenantId, long lastSeq, String lastHash, Instant updatedAt) {
        auditLogMapper.updateChainState(tenantId, lastSeq, lastHash, updatedAt);
    }

    public void insertExportLog(UUID id, UUID tenantId, UUID requestedBy, String format, Instant fromUtc, Instant toUtc, int rowCount, UUID traceId) {
        auditLogMapper.insertExportLog(id, tenantId, requestedBy, format, fromUtc, toUtc, rowCount, traceId);
    }

    public void insertExportJob(
        UUID id,
        UUID tenantId,
        UUID requestedBy,
        String status,
        String exportFormat,
        Instant fromUtc,
        Instant toUtc,
        int rowLimit,
        int maxBytes,
        int maxDurationSec,
        Instant expiresAt,
        UUID traceId,
        Instant createdAt
    ) {
        auditLogMapper.insertExportJob(
            id,
            tenantId,
            requestedBy,
            status,
            exportFormat,
            fromUtc,
            toUtc,
            rowLimit,
            maxBytes,
            maxDurationSec,
            expiresAt,
            traceId,
            createdAt
        );
    }

    public Optional<AuditExportJobRecord> findExportJobById(UUID tenantId, UUID jobId) {
        return Optional.ofNullable(auditLogMapper.findExportJobById(tenantId, jobId));
    }

    public Optional<AuditExportJobRecord> findExportJobByIdForAnyTenant(UUID jobId) {
        return Optional.ofNullable(auditLogMapper.findExportJobByIdAnyTenant(jobId));
    }

    public List<AuditExportJobRecord> findPendingExportJobs(Instant nowUtc, int limit) {
        return auditLogMapper.findPendingExportJobs(nowUtc, limit);
    }

    public boolean claimExportJob(UUID jobId, Instant startedAt) {
        return auditLogMapper.claimExportJob(jobId, startedAt) == 1;
    }

    public void markExportJobDone(UUID jobId, int rowCount, int totalBytes, Instant completedAt) {
        auditLogMapper.markExportJobDone(jobId, rowCount, totalBytes, completedAt);
    }

    public void markExportJobFailed(UUID jobId, String errorCode, String errorMessage, Instant completedAt) {
        auditLogMapper.markExportJobFailed(jobId, errorCode, errorMessage, completedAt);
    }

    public List<AuditExportJobRecord> findJobsToExpire(Instant nowUtc, int limit) {
        return auditLogMapper.findJobsToExpire(nowUtc, limit);
    }

    public boolean markExportJobExpired(UUID jobId, Instant completedAt) {
        return auditLogMapper.markExportJobExpired(jobId, completedAt) == 1;
    }

    public void insertExportChunk(UUID jobId, int chunkNo, byte[] payloadBytes, String payloadHash, Instant createdAt) {
        auditLogMapper.insertExportChunk(jobId, chunkNo, payloadBytes, payloadHash, createdAt);
    }

    public List<AuditExportChunkRecord> findExportChunks(UUID jobId) {
        return auditLogMapper.findExportChunks(jobId);
    }

    public void deleteExportChunks(UUID jobId) {
        auditLogMapper.deleteExportChunks(jobId);
    }
}
