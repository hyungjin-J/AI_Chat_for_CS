package com.aichatbot.contexts.operations.application;

import com.aichatbot.contexts.operations.domain.OpsBlockRecord;
import com.aichatbot.contexts.operations.domain.port.OpsBlockStore;
import java.time.Clock;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class OpsBlockService {

    private final OpsBlockStore opsRepository;
    private final Clock clock;

    @Autowired
    public OpsBlockService(OpsBlockStore opsRepository) {
        this(opsRepository, Clock.systemUTC());
    }

    OpsBlockService(OpsBlockStore opsRepository, Clock clock) {
        this.opsRepository = opsRepository;
        this.clock = clock;
    }

    public void upsert(
        UUID tenantId,
        String blockType,
        String blockValue,
        String status,
        String reason,
        Instant expiresAt,
        UUID createdBy
    ) {
        opsRepository.upsertBlock(
            tenantId,
            normalizeBlockType(blockType),
            normalizeBlockValue(blockValue),
            status == null || status.isBlank() ? "ACTIVE" : status.trim().toUpperCase(),
            reason,
            expiresAt,
            createdBy,
            Instant.now(clock)
        );
    }

    public Optional<OpsBlockRecord> findActive(UUID tenantId, String blockType, String blockValue) {
        return opsRepository.findActiveBlock(
            tenantId,
            normalizeBlockType(blockType),
            normalizeBlockValue(blockValue),
            Instant.now(clock)
        );
    }

    private String normalizeBlockType(String blockType) {
        return (blockType == null ? "" : blockType.trim().toUpperCase());
    }

    private String normalizeBlockValue(String blockValue) {
        return blockValue == null ? "" : blockValue.trim();
    }
}

