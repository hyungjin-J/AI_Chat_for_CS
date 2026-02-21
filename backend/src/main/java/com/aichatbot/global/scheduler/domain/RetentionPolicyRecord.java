package com.aichatbot.global.scheduler.domain;

public record RetentionPolicyRecord(
    String tableName,
    int retentionDays,
    boolean enabled
) {
}
