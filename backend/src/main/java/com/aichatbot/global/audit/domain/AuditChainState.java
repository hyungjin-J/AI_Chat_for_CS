package com.aichatbot.global.audit.domain;

import java.util.UUID;

public record AuditChainState(
    UUID tenantId,
    Long lastSeq,
    String lastHash
) {
}
