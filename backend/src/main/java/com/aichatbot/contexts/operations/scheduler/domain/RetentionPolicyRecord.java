package com.aichatbot.contexts.operations.scheduler.domain;

public record RetentionPolicyRecord(
    String tableName,
    int retentionDays,
    boolean enabled
) {
}

