package com.aichatbot.global.tenant;

import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.observability.TraceContext;
import java.io.IOException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Objects;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class TenantKeyFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        String tenantKey = request.getHeader("X-Tenant-Key");

        // 왜 필요한가: 테넌트 키가 없으면 데이터가 섞일 수 있으므로 서버에서 즉시 차단한다.
        if (tenantKey == null || tenantKey.isBlank()) {
            writeBadRequest(response);
            return;
        }

        TenantContext.setTenantKey(tenantKey.trim());
        try {
            filterChain.doFilter(request, response);
        } finally {
            TenantContext.clear();
        }
    }

    private void writeBadRequest(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.BAD_REQUEST.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");

        ApiErrorResponse body = new ApiErrorResponse(
            "SEC-001-TENANT-KEY-REQUIRED",
            "X-Tenant-Key 헤더가 필요합니다.",
            TraceContext.getTraceId()
        );
        response.getWriter().write(toJson(body));
    }

    private String toJson(ApiErrorResponse body) {
        // 왜 필요한가: 빌드 의존성을 최소화하면서도 표준 JSON 에러 형태를 유지하기 위함이다.
        String safeMessage = escapeJson(body.message());
        String safeTraceId = escapeJson(body.traceId() == null ? "" : body.traceId());
        return "{\"error_code\":\"" + body.errorCode() + "\",\"message\":\"" + safeMessage + "\",\"trace_id\":\"" + safeTraceId + "\"}";
    }

    private String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return Objects.equals(request.getRequestURI(), "/health")
            || Objects.equals(request.getRequestURI(), "/actuator/health");
    }
}
