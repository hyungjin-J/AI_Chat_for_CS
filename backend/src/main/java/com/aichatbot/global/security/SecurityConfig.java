package com.aichatbot.global.security;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.audit.AuditLogService;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.ops.application.OpsEventService;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import java.util.UUID;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    private final ObjectMapper objectMapper;
    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final AppProperties appProperties;
    private final OpsEventService opsEventService;
    private final AuditLogService auditLogService;

    public SecurityConfig(
        ObjectMapper objectMapper,
        JwtAuthenticationFilter jwtAuthenticationFilter,
        AppProperties appProperties,
        OpsEventService opsEventService,
        AuditLogService auditLogService
    ) {
        this.objectMapper = objectMapper;
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.appProperties = appProperties;
        this.opsEventService = opsEventService;
        this.auditLogService = auditLogService;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        RoleHeaderAuthenticationFilter roleHeaderAuthenticationFilter =
            new RoleHeaderAuthenticationFilter(appProperties.getSecurity().isAllowHeaderAuth());

        // Why: 운영 API는 서버측 RBAC를 강제해야 하며 UI 차단만으로는 권한 경계를 보장할 수 없다.
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/error").permitAll()
                .requestMatchers("/health", "/actuator/health", "/actuator/prometheus").permitAll()
                .requestMatchers("/v1/auth/login", "/v1/auth/refresh").permitAll()
                // Why: 레거시 데모 경로(/api/v1)는 우회 접근 위험이 있어 운영 경로에서 명시적으로 차단한다.
                .requestMatchers("/api/v1/**").denyAll()
                .requestMatchers(HttpMethod.GET, "/v1/chat/bootstrap").hasRole("AGENT")
                .requestMatchers(HttpMethod.POST, "/v1/sessions").hasRole("AGENT")
                .requestMatchers(HttpMethod.GET, "/v1/sessions/*").hasRole("AGENT")
                .requestMatchers(HttpMethod.GET, "/v1/sessions/*/messages").hasRole("AGENT")
                .requestMatchers(HttpMethod.POST, "/v1/sessions/*/messages").hasRole("AGENT")
                .requestMatchers(HttpMethod.GET, "/v1/sessions/*/messages/*/stream").hasRole("AGENT")
                .requestMatchers(HttpMethod.GET, "/v1/sessions/*/messages/*/stream/resume").hasRole("AGENT")
                .requestMatchers(HttpMethod.POST, "/v1/rag/retrieve").hasRole("SYSTEM")
                .requestMatchers(HttpMethod.POST, "/v1/rag/answer").hasRole("SYSTEM")
                .requestMatchers(HttpMethod.GET, "/v1/rag/answers/*/citations").hasRole("AGENT")
                .requestMatchers(HttpMethod.GET, "/v1/admin/tenants/*/usage-report").hasAnyRole("OPS", "ADMIN")
                .requestMatchers(HttpMethod.PUT, "/v1/admin/tenants/*/quota").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET, "/v1/admin/dashboard/summary").hasRole("OPS")
                .requestMatchers(HttpMethod.GET, "/v1/admin/dashboard/series").hasRole("OPS")
                .requestMatchers(HttpMethod.GET, "/v1/admin/audit-logs").hasRole("OPS")
                .requestMatchers(HttpMethod.GET, "/v1/admin/audit-logs/*/diff").hasRole("OPS")
                .requestMatchers(HttpMethod.GET, "/v1/admin/audit-logs/export").hasRole("OPS")
                .requestMatchers(HttpMethod.GET, "/v1/admin/audit-logs/chain-verify").hasRole("OPS")
                .requestMatchers(HttpMethod.PUT, "/v1/admin/rbac/matrix/*").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET, "/v1/admin/rbac/approval-requests").hasRole("ADMIN")
                .requestMatchers(HttpMethod.POST, "/v1/admin/rbac/approval-requests/*/approve").hasRole("ADMIN")
                .requestMatchers(HttpMethod.POST, "/v1/admin/rbac/approval-requests/*/reject").hasRole("ADMIN")
                .requestMatchers(HttpMethod.PUT, "/v1/ops/blocks/*").hasRole("OPS")
                .requestMatchers(HttpMethod.POST, "/v1/auth/logout").authenticated()
                .requestMatchers(HttpMethod.GET, "/v1/auth/sessions").authenticated()
                .requestMatchers(HttpMethod.DELETE, "/v1/auth/sessions/*").authenticated()
                .requestMatchers(HttpMethod.POST, "/v1/auth/sessions/revoke-others").authenticated()
                .requestMatchers(HttpMethod.POST, "/v1/auth/mfa/**").permitAll()
                .anyRequest().authenticated()
            )
            .exceptionHandling(handling -> handling
                .authenticationEntryPoint((request, response, authException) ->
                    writeError(
                        response,
                        HttpStatus.UNAUTHORIZED,
                        "SEC-001-401",
                        ErrorCatalog.messageOf("SEC-001-401"),
                        List.of("authentication_required")
                    )
                )
                .accessDeniedHandler((request, response, accessDeniedException) ->
                    {
                        try {
                            if (TenantContext.getTenantId() != null) {
                                UUID tenantId = UUID.fromString(TenantContext.getTenantId());
                                opsEventService.append(
                                    tenantId,
                                    "RBAC_DENIED",
                                    "rbac_denied",
                                    1L,
                                    Map.of("path", request.getRequestURI(), "method", request.getMethod())
                                );
                                UserPrincipal principal = PrincipalUtils.currentPrincipal();
                                auditLogService.write(
                                    tenantId,
                                    "RBAC_DENIED",
                                    AuditLogService.toUuidOrNull(principal.userId()),
                                    String.join(",", principal.roles()),
                                    "HTTP_ENDPOINT",
                                    request.getRequestURI(),
                                    null,
                                    Map.of("method", request.getMethod())
                                );
                            }
                        } catch (Exception ignored) {
                            // Keep deny response path robust even if audit linkage fails.
                        }
                        writeError(
                            response,
                            HttpStatus.FORBIDDEN,
                            "SEC-002-403",
                            ErrorCatalog.messageOf("SEC-002-403"),
                            List.of("rbac_denied")
                        );
                    }
                )
            )
            .addFilterAfter(jwtAuthenticationFilter, SecurityContextHolderFilter.class)
            .addFilterAfter(roleHeaderAuthenticationFilter, JwtAuthenticationFilter.class);

        return http.build();
    }

    private void writeError(
        HttpServletResponse response,
        HttpStatus status,
        String errorCode,
        String message,
        List<String> details
    ) throws IOException {
        response.setStatus(status.value());
        response.setCharacterEncoding("UTF-8");
        response.setContentType("application/json;charset=UTF-8");
        ApiErrorResponse body = new ApiErrorResponse(errorCode, message, TraceContext.getTraceId(), details);
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
