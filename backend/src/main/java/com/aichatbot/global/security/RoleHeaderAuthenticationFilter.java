package com.aichatbot.global.security;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.stream.Collectors;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.web.filter.OncePerRequestFilter;

public class RoleHeaderAuthenticationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() == null) {
            String roleHeader = request.getHeader("X-User-Role");
            String userIdHeader = request.getHeader("X-User-Id");

            if (roleHeader != null && !roleHeader.isBlank()) {
                List<SimpleGrantedAuthority> authorities = Arrays.stream(roleHeader.split(","))
                    .map(role -> role.trim().toUpperCase(Locale.ROOT))
                    .filter(role -> !role.isBlank())
                    .map(role -> role.startsWith("ROLE_") ? role : "ROLE_" + role)
                    .map(SimpleGrantedAuthority::new)
                    .collect(Collectors.toList());

                if (!authorities.isEmpty()) {
                    String principal = (userIdHeader == null || userIdHeader.isBlank()) ? "header-user" : userIdHeader.trim();
                    UsernamePasswordAuthenticationToken authentication =
                        new UsernamePasswordAuthenticationToken(principal, "N/A", authorities);
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                }
            }
        }

        try {
            filterChain.doFilter(request, response);
        } finally {
            // Why: ThreadLocal 기반 SecurityContext는 재사용 스레드에서 누수를 막기 위해 요청 종료 시 정리한다.
            SecurityContextHolder.clearContext();
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return Objects.equals(request.getRequestURI(), "/health")
            || Objects.equals(request.getRequestURI(), "/actuator/health");
    }
}
