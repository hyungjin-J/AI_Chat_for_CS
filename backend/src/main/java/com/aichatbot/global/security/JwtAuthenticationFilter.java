package com.aichatbot.global.security;

import com.aichatbot.auth.application.AuthService;
import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.tenant.TenantContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final AuthService authService;
    private final ObjectMapper objectMapper;

    public JwtAuthenticationFilter(AuthService authService, ObjectMapper objectMapper) {
        this.authService = authService;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() != null) {
            filterChain.doFilter(request, response);
            return;
        }

        String authorization = request.getHeader("Authorization");
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        String accessToken = authorization.substring("Bearer ".length()).trim();
        if (accessToken.isBlank()) {
            writeUnauthorized(response);
            return;
        }

        try {
            UserPrincipal principal = authService.parseAccessToken(accessToken);
            if (TenantContext.getTenantId() != null && !TenantContext.getTenantId().equals(principal.tenantId())) {
                writeForbiddenTenant(response);
                return;
            }

            UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                principal,
                "N/A",
                principal.roles().stream()
                    .map(role -> role.startsWith("ROLE_") ? role : "ROLE_" + role)
                    .map(SimpleGrantedAuthority::new)
                    .collect(Collectors.toList())
            );
            SecurityContextHolder.getContext().setAuthentication(authentication);
            filterChain.doFilter(request, response);
        } catch (Exception exception) {
            writeUnauthorized(response);
        }
    }

    private void writeUnauthorized(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");
        ApiErrorResponse body = new ApiErrorResponse(
            "SEC-001-401",
            ErrorCatalog.messageOf("SEC-001-401"),
            TraceContext.getTraceId(),
            List.of("invalid_or_expired_token")
        );
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }

    private void writeForbiddenTenant(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.FORBIDDEN.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");
        ApiErrorResponse body = new ApiErrorResponse(
            "SYS-002-403",
            ErrorCatalog.messageOf("SYS-002-403"),
            TraceContext.getTraceId(),
            List.of("tenant_mismatch")
        );
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        return uri.equals("/v1/auth/login")
            || uri.equals("/v1/auth/refresh")
            || uri.equals("/health")
            || uri.equals("/actuator/health")
            || uri.startsWith("/error");
    }
}
