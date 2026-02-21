package com.aichatbot.auth.application;

import com.aichatbot.global.config.AppProperties;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Service
public class AuthRateLimitService {

    private static final Logger log = LoggerFactory.getLogger(AuthRateLimitService.class);

    private final StringRedisTemplate redisTemplate;
    private final AppProperties appProperties;
    private final Clock clock;

    @Autowired
    public AuthRateLimitService(StringRedisTemplate redisTemplate, AppProperties appProperties) {
        this(redisTemplate, appProperties, Clock.systemUTC());
    }

    AuthRateLimitService(StringRedisTemplate redisTemplate, AppProperties appProperties, Clock clock) {
        this.redisTemplate = redisTemplate;
        this.appProperties = appProperties;
        this.clock = clock;
    }

    public RateLimitDecision consumeLoginAttempt(String tenantKey, String ipAddress) {
        Instant nowUtc = Instant.now(clock);
        long epochMinuteUtc = nowUtc.atZone(ZoneOffset.UTC).toEpochSecond() / 60L;
        long windowEndEpochSeconds = (epochMinuteUtc + 1L) * 60L;
        long retryAfterSeconds = Math.max(0L, windowEndEpochSeconds - nowUtc.getEpochSecond());
        long limit = Math.max(1L, appProperties.getAuth().getRateLimitPerMinute());
        String key = appProperties.getAuth().getRateLimitRedisKeyPrefix()
            + tenantKey + ":" + ipAddress + ":" + epochMinuteUtc;
        try {
            Long current = redisTemplate.opsForValue().increment(key);
            if (current != null && current == 1L) {
                redisTemplate.expire(key, Duration.ofSeconds(Math.max(1L, retryAfterSeconds)));
            }
            long currentCount = current == null ? 0L : current;
            boolean allowed = currentCount <= limit;
            long remaining = Math.max(0L, limit - currentCount);
            return new RateLimitDecision(allowed, limit, remaining, windowEndEpochSeconds, retryAfterSeconds);
        } catch (DataAccessException exception) {
            log.warn("auth rate-limit redis unavailable, fail-open tenant={} ip={}", tenantKey, ipAddress, exception);
            return new RateLimitDecision(true, limit, limit, windowEndEpochSeconds, 0L);
        }
    }

    public record RateLimitDecision(
        boolean allowed,
        long limit,
        long remaining,
        long resetEpochSeconds,
        long retryAfterSeconds
    ) {
    }
}
