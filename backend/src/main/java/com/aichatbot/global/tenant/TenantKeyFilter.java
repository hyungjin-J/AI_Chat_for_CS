package com.aichatbot.global.tenant;

import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class TenantKeyFilter extends OncePerRequestFilter {

    private final TenantResolverRepository tenantResolverRepository;
    private final ObjectMapper objectMapper;

    public TenantKeyFilter(TenantResolverRepository tenantResolverRepository, ObjectMapper objectMapper) {
        this.tenantResolverRepository = tenantResolverRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        String tenantKey = request.getHeader("X-Tenant-Key");

        if (tenantKey == null || tenantKey.isBlank()) {
            writeForbidden(response, List.of("missing_tenant_key"));
            return;
        }

        Optional<UUID> tenantIdOptional = tenantResolverRepository.findTenantIdByKey(tenantKey.trim());
        if (tenantIdOptional.isEmpty()) {
            writeForbidden(response, List.of("tenant_not_found"));
            return;
        }

        TenantContext.setTenantKey(tenantKey.trim());
        TenantContext.setTenantId(tenantIdOptional.get().toString());
        try {
            filterChain.doFilter(request, response);
        } finally {
            TenantContext.clear();
        }
    }

    private void writeForbidden(HttpServletResponse response, List<String> details) throws IOException {
        response.setStatus(HttpStatus.FORBIDDEN.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");
        ApiErrorResponse body = new ApiErrorResponse(
            "SYS-002-403",
            ErrorCatalog.messageOf("SYS-002-403"),
            TraceContext.getTraceId(),
            details
        );
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        return Objects.equals(uri, "/health")
            || Objects.equals(uri, "/actuator/health")
            || Objects.equals(uri, "/actuator/prometheus")
            || uri.startsWith("/error");
    }
}
