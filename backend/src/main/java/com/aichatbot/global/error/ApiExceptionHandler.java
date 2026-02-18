package com.aichatbot.global.error;

import com.aichatbot.global.observability.TraceContext;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(QuotaExceededException.class)
    public ResponseEntity<ApiErrorResponse> handleQuotaExceeded(QuotaExceededException exception) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Retry-After", String.valueOf(exception.retryAfterSeconds()));
        headers.add("X-RateLimit-Limit", String.valueOf(exception.limit()));
        headers.add("X-RateLimit-Remaining", String.valueOf(exception.remaining()));
        headers.add("X-RateLimit-Reset", String.valueOf(exception.resetEpochSeconds()));

        ApiErrorResponse error = new ApiErrorResponse(
            exception.errorCode(),
            exception.getMessage(),
            TraceContext.getTraceId(),
            exception.details()
        );
        return new ResponseEntity<>(error, headers, exception.status());
    }

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiErrorResponse> handleApiException(ApiException exception) {
        ApiErrorResponse error = new ApiErrorResponse(
            exception.errorCode(),
            exception.getMessage(),
            TraceContext.getTraceId(),
            exception.details()
        );
        return ResponseEntity.status(exception.status()).body(error);
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiErrorResponse> handleAccessDenied(AccessDeniedException exception) {
        ApiErrorResponse error = new ApiErrorResponse(
            "SEC-002-403",
            ErrorCatalog.messageOf("SEC-002-403"),
            TraceContext.getTraceId(),
            List.of("rbac_denied")
        );
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(error);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse> handleValidation(MethodArgumentNotValidException exception) {
        List<String> details = exception.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .toList();
        ApiErrorResponse error = new ApiErrorResponse(
            "API-003-422",
            ErrorCatalog.messageOf("API-003-422"),
            TraceContext.getTraceId(),
            details
        );
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(error);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiErrorResponse> handleIllegalArgument(IllegalArgumentException exception) {
        ApiErrorResponse error = new ApiErrorResponse(
            "API-003-422",
            ErrorCatalog.messageOf("API-003-422"),
            TraceContext.getTraceId(),
            List.of(exception.getMessage())
        );
        return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(error);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleException(Exception exception) {
        log.error("Unhandled exception trace_id={}", TraceContext.getTraceId(), exception);
        // Why: 예외 응답 스키마를 고정해야 운영 파이프라인에서 자동 파싱과 경보 라우팅이 가능하다.
        ApiErrorResponse error = new ApiErrorResponse(
            "SYS-003-500",
            ErrorCatalog.messageOf("SYS-003-500"),
            TraceContext.getTraceId(),
            List.of(exception.getClass().getSimpleName())
        );
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}
