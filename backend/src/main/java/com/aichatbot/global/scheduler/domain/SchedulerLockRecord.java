package com.aichatbot.global.scheduler.domain;

import java.time.Instant;
import java.util.UUID;

public record SchedulerLockRecord(
    String lockKey,
    UUID ownerId,
    Instant leaseUntilUtc,
    Long fencingToken,
    Instant updatedAt,
    Instant lastHeartbeatUtc,
    Instant lastRecoveredAt,
    Long recoveryCount
) {
}
