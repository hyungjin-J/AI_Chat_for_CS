package com.aichatbot.global.error;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record ApiErrorResponse(
    @JsonProperty("error_code")
    String errorCode,
    String message,
    @JsonProperty("trace_id")
    String traceId,
    @JsonInclude(JsonInclude.Include.NON_EMPTY)
    List<String> details
) {

    public ApiErrorResponse(String errorCode, String message, String traceId) {
        this(errorCode, message, traceId, List.of());
    }
}
