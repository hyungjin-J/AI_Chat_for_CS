package com.aichatbot.global.audit.export;

import com.aichatbot.global.audit.PersistentAuditLogRepository;
import com.aichatbot.global.audit.domain.AuditExportChunkRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class DbExportStorage extends ExportStorage {

    private final PersistentAuditLogRepository auditLogRepository;

    public DbExportStorage(PersistentAuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @Override
    public void storeChunk(UUID jobId, int chunkNo, byte[] payloadBytes, String payloadHash, Instant createdAt) {
        auditLogRepository.insertExportChunk(jobId, chunkNo, payloadBytes, payloadHash, createdAt);
    }

    @Override
    public List<AuditExportChunkRecord> readChunks(UUID jobId) {
        return auditLogRepository.findExportChunks(jobId);
    }

    @Override
    public void expireJobPayload(UUID jobId) {
        auditLogRepository.deleteExportChunks(jobId);
    }
}
