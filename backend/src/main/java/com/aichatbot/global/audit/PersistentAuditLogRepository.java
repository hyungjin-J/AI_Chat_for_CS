package com.aichatbot.global.audit;

import com.aichatbot.global.audit.domain.AuditChainState;
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
}
