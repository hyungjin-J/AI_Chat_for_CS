package com.aichatbot.global.error;

import java.util.List;
import org.springframework.http.HttpStatus;

public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String errorCode;
    private final List<String> details;

    public ApiException(HttpStatus status, String errorCode, String message) {
        this(status, errorCode, message, List.of());
    }

    public ApiException(HttpStatus status, String errorCode, String message, List<String> details) {
        super(message);
        this.status = status;
        this.errorCode = errorCode;
        this.details = details == null ? List.of() : List.copyOf(details);
    }

    public HttpStatus status() {
        return status;
    }

    public String errorCode() {
        return errorCode;
    }

    public List<String> details() {
        return details;
    }
}

