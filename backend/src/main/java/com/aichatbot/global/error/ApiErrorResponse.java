package com.aichatbot.global.error;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ApiErrorResponse(
    @JsonProperty("error_code")
    String errorCode,
    String message,
    @JsonProperty("trace_id")
    String traceId
) {
}
