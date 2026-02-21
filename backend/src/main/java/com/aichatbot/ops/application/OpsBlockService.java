package com.aichatbot.ops.application;

import com.aichatbot.ops.domain.OpsBlockRecord;
import com.aichatbot.ops.infrastructure.OpsRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class OpsBlockService {

    private final OpsRepository opsRepository;
    private final Clock clock;

    @Autowired
    public OpsBlockService(OpsRepository opsRepository) {
        this(opsRepository, Clock.systemUTC());
    }

    OpsBlockService(OpsRepository opsRepository, Clock clock) {
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
