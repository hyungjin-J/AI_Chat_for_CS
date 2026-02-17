package com.aichatbot.global.security;

import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.observability.TraceContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
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

    public SecurityConfig(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        RoleHeaderAuthenticationFilter roleHeaderAuthenticationFilter = new RoleHeaderAuthenticationFilter();

        // Why: 운영 API는 서버측 RBAC를 강제해야 하며 UI 차단만으로는 권한 경계를 보장할 수 없다.
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/health", "/actuator/health").permitAll()
                .requestMatchers(HttpMethod.GET, "/v1/admin/tenants/*/usage-report").hasAnyRole("OPS", "ADMIN")
                .requestMatchers(HttpMethod.PUT, "/v1/admin/tenants/*/quota").hasRole("ADMIN")
                .anyRequest().permitAll()
            )
            .exceptionHandling(handling -> handling
                .authenticationEntryPoint((request, response, authException) ->
                    writeError(response, HttpStatus.UNAUTHORIZED, "SEC-001-UNAUTHORIZED", "Authentication required", List.of("missing_auth"))
                )
                .accessDeniedHandler((request, response, accessDeniedException) ->
                    writeError(response, HttpStatus.FORBIDDEN, "API-403", "Forbidden", List.of("rbac_denied"))
                )
            )
            .addFilterAfter(roleHeaderAuthenticationFilter, SecurityContextHolderFilter.class);

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
