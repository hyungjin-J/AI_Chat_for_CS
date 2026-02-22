package com.aichatbot.platform.observability;

import com.aichatbot.platform.error.ApiException;
import com.aichatbot.platform.error.ErrorCatalog;
import java.util.List;
import org.springframework.http.HttpStatus;

public final class TraceGuard {

    private TraceGuard() {
    }

    public static String requireTraceId() {
        String traceId = TraceContext.getTraceId();
        if (traceId == null || traceId.isBlank()) {
            throw new ApiException(
                HttpStatus.CONFLICT,
                "SYS-004-409-TRACE",
                ErrorCatalog.messageOf("SYS-004-409-TRACE"),
                List.of("trace_id_missing")
            );
        }
        return traceId;
    }
}

