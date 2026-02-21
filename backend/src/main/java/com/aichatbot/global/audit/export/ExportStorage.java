package com.aichatbot.global.audit.export;

import com.aichatbot.global.audit.domain.AuditExportChunkRecord;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public abstract class ExportStorage {

    public abstract void storeChunk(UUID jobId, int chunkNo, byte[] payloadBytes, String payloadHash, Instant createdAt);

    public abstract List<AuditExportChunkRecord> readChunks(UUID jobId);

    public abstract void expireJobPayload(UUID jobId);
}
