package com.aichatbot.global.error;

import com.aichatbot.global.observability.TraceContext;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleException(Exception exception) {
        // 왜 필요한가: 예외 형태를 통일해야 프론트/운영이 일관되게 대응할 수 있다.
        ApiErrorResponse error = new ApiErrorResponse(
            "SYS-003-UNEXPECTED",
            "예상하지 못한 오류가 발생했습니다.",
            TraceContext.getTraceId()
        );
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}
