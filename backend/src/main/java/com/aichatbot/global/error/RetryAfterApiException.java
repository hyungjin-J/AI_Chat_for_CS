package com.aichatbot.global.error;

import java.util.List;
import org.springframework.http.HttpStatus;

public class RetryAfterApiException extends ApiException {

    private final long retryAfterSeconds;
    private final Long limit;
    private final Long remaining;
    private final Long resetEpochSeconds;

    public RetryAfterApiException(
        HttpStatus status,
        String errorCode,
        String message,
        List<String> details,
        long retryAfterSeconds,
        Long limit,
        Long remaining,
        Long resetEpochSeconds
    ) {
        super(status, errorCode, message, details);
        this.retryAfterSeconds = Math.max(0L, retryAfterSeconds);
        this.limit = limit;
        this.remaining = remaining;
        this.resetEpochSeconds = resetEpochSeconds;
    }

    public long retryAfterSeconds() {
        return retryAfterSeconds;
    }

    public Long limit() {
        return limit;
    }

    public Long remaining() {
        return remaining;
    }

    public Long resetEpochSeconds() {
        return resetEpochSeconds;
    }
}

