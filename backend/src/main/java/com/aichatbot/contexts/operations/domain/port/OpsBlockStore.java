package com.aichatbot.contexts.operations.domain.port;

import com.aichatbot.contexts.operations.domain.OpsBlockRecord;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public interface OpsBlockStore {

    void upsertBlock(
        UUID tenantId,
        String blockType,
        String blockValue,
        String status,
        String reason,
        Instant expiresAt,
        UUID createdBy,
        Instant updatedAt
    );

    Optional<OpsBlockRecord> findActiveBlock(UUID tenantId, String blockType, String blockValue, Instant nowUtc);
}
