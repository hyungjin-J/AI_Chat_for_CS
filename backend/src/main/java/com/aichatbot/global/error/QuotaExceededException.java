package com.aichatbot.global.error;

import java.util.List;
import org.springframework.http.HttpStatus;

public class QuotaExceededException extends ApiException {

    private final long limit;
    private final long remaining;
    private final long resetEpochSeconds;
    private final long retryAfterSeconds;

    public QuotaExceededException(
        HttpStatus status,
        String errorCode,
        String message,
        long limit,
        long remaining,
        long resetEpochSeconds,
        long retryAfterSeconds
    ) {
        super(status, errorCode, message, List.of("quota_exceeded"));
        this.limit = limit;
        this.remaining = remaining;
        this.resetEpochSeconds = resetEpochSeconds;
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public long limit() {
        return limit;
    }

    public long remaining() {
        return remaining;
    }

    public long resetEpochSeconds() {
        return resetEpochSeconds;
    }

    public long retryAfterSeconds() {
        return retryAfterSeconds;
    }
}

