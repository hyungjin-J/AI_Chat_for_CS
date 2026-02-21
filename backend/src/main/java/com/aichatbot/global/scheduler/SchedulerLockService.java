package com.aichatbot.global.scheduler;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class SchedulerLockService {

    private final SchedulerRepository schedulerRepository;
    private final Clock clock;
    private final UUID ownerId;

    @Autowired
    public SchedulerLockService(SchedulerRepository schedulerRepository) {
        this(schedulerRepository, Clock.systemUTC());
    }

    SchedulerLockService(SchedulerRepository schedulerRepository, Clock clock) {
        this.schedulerRepository = schedulerRepository;
        this.clock = clock;
        this.ownerId = buildOwnerId();
    }

    public boolean tryAcquire(String lockKey, Duration leaseDuration) {
        Instant nowUtc = Instant.now(clock);
        Instant leaseUntilUtc = nowUtc.plus(leaseDuration == null ? Duration.ofMinutes(2) : leaseDuration);
        return schedulerRepository.tryAcquireLock(lockKey, ownerId, nowUtc, leaseUntilUtc);
    }

    private UUID buildOwnerId() {
        return UUID.randomUUID();
    }
}
