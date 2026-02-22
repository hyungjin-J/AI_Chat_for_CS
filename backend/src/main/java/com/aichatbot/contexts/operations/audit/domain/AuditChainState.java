package com.aichatbot.contexts.operations.audit.domain;

import java.util.UUID;

public record AuditChainState(
    UUID tenantId,
    Long lastSeq,
    String lastHash
) {
}

