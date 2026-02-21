package com.aichatbot.global.scheduler;

import com.aichatbot.global.scheduler.domain.SchedulerLockRecord;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class SchedulerLockService {

    private static final Logger log = LoggerFactory.getLogger(SchedulerLockService.class);

    private final SchedulerRepository schedulerRepository;
    private final Clock clock;
    private final UUID ownerId;
    private final MeterRegistry meterRegistry;

    @Autowired
    public SchedulerLockService(SchedulerRepository schedulerRepository, @Autowired(required = false) MeterRegistry meterRegistry) {
        this(schedulerRepository, Clock.systemUTC(), meterRegistry);
    }

    SchedulerLockService(SchedulerRepository schedulerRepository, Clock clock, MeterRegistry meterRegistry) {
        this.schedulerRepository = schedulerRepository;
        this.clock = clock;
        this.meterRegistry = meterRegistry;
        this.ownerId = buildOwnerId();
    }

    public boolean tryAcquire(String lockKey, Duration leaseDuration) {
        Instant nowUtc = Instant.now(clock);
        Instant leaseUntilUtc = nowUtc.plus(leaseDuration == null ? Duration.ofMinutes(2) : leaseDuration);
        boolean acquired = schedulerRepository.tryAcquireLock(lockKey, ownerId, nowUtc, leaseUntilUtc);
        emitLockEvent(lockKey, acquired ? "acquired" : "skipped");
        return acquired;
    }

    public boolean heartbeat(String lockKey, Duration leaseDuration) {
        Instant nowUtc = Instant.now(clock);
        Instant leaseUntilUtc = nowUtc.plus(leaseDuration == null ? Duration.ofMinutes(2) : leaseDuration);
        boolean ok = schedulerRepository.heartbeatLock(lockKey, ownerId, leaseUntilUtc, nowUtc);
        emitLockEvent(lockKey, ok ? "heartbeat_ok" : "heartbeat_miss");
        return ok;
    }

    public boolean forceRecoverStaleLock(String lockKey, Duration leaseDuration) {
        Instant nowUtc = Instant.now(clock);
        Instant leaseUntilUtc = nowUtc.plus(leaseDuration == null ? Duration.ofMinutes(2) : leaseDuration);
        boolean recovered = schedulerRepository.forceRecoverStaleLock(lockKey, ownerId, leaseUntilUtc, nowUtc);
        emitLockEvent(lockKey, recovered ? "recovered" : "recover_miss");
        return recovered;
    }

    public List<SchedulerLockRecord> findStaleLocks(Duration staleThreshold, int limit) {
        Instant nowUtc = Instant.now(clock);
        Instant staleBeforeUtc = nowUtc.minus(staleThreshold == null ? Duration.ofMinutes(5) : staleThreshold);
        return schedulerRepository.findStaleLocks(nowUtc, staleBeforeUtc, Math.max(1, limit));
    }

    public void emitLockEvent(String lockKey, String outcome) {
        log.info("scheduler_lock_event lock_key={} outcome={} owner_id={}", lockKey, outcome, ownerId);
        if (meterRegistry != null) {
            meterRegistry.counter("scheduler_lock_events_total", "lock_key", lockKey, "outcome", outcome).increment();
        }
    }

    public UUID ownerId() {
        return ownerId;
    }

    private UUID buildOwnerId() {
        return UUID.randomUUID();
    }
}
