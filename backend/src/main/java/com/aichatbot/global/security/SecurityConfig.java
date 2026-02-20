package com.aichatbot.global.security;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiErrorResponse;
import com.aichatbot.global.error.ErrorCatalog;
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
    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final AppProperties appProperties;

    public SecurityConfig(
        ObjectMapper objectMapper,
        JwtAuthenticationFilter jwtAuthenticationFilter,
        AppProperties appProperties
    ) {
        this.objectMapper = objectMapper;
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.appProperties = appProperties;
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
                .requestMatchers("/api/v1/**").permitAll()
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
                .requestMatchers(HttpMethod.POST, "/v1/auth/logout").authenticated()
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
                    writeError(
                        response,
                        HttpStatus.FORBIDDEN,
                        "SEC-002-403",
                        ErrorCatalog.messageOf("SEC-002-403"),
                        List.of("rbac_denied")
                    )
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
