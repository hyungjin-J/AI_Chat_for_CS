package com.aichatbot.global.observability;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.error.ErrorCatalog;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {

    private final AppProperties appProperties;
    private final ObjectMapper objectMapper;

    public TraceIdFilter(AppProperties appProperties, ObjectMapper objectMapper) {
        this.appProperties = appProperties;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        String traceId = request.getHeader("X-Trace-Id");
        if (traceId == null || traceId.isBlank()) {
            if (appProperties.getTrace().isRequireHeader()) {
                writeTraceError(response);
                return;
            }
            traceId = UUID.randomUUID().toString();
        } else {
            try {
                UUID.fromString(traceId.trim());
                traceId = traceId.trim();
            } catch (IllegalArgumentException exception) {
                writeTraceError(response, List.of("invalid_trace_id_format"));
                return;
            }
        }

        TraceContext.setTraceId(traceId);
        response.setHeader("X-Trace-Id", traceId);

        try {
            filterChain.doFilter(request, response);
        } finally {
            TraceContext.clear();
        }
    }

    private void writeTraceError(HttpServletResponse response) throws IOException {
        writeTraceError(response, List.of("missing_trace_id"));
    }

    private void writeTraceError(HttpServletResponse response, List<String> details) throws IOException {
        response.setStatus(HttpStatus.CONFLICT.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");
        ApiErrorResponse body = new ApiErrorResponse(
            "SYS-004-409-TRACE",
            ErrorCatalog.messageOf("SYS-004-409-TRACE"),
            null,
            details
        );
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
