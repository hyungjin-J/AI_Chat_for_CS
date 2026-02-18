package com.aichatbot.auth.application;

import com.aichatbot.auth.domain.AuthUser;
import com.aichatbot.auth.infrastructure.AuthRepository;
import com.aichatbot.auth.presentation.dto.AuthTokenResponse;
import com.aichatbot.auth.presentation.dto.LoginRequest;
import com.aichatbot.auth.presentation.dto.LogoutRequest;
import com.aichatbot.auth.presentation.dto.RefreshRequest;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.UserPrincipal;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private static final Map<String, String> MVP_PASSWORDS = Map.of(
        "agent1", "agent1-pass",
        "admin1", "admin1-pass",
        "ops1", "ops1-pass"
    );

    private final AuthRepository authRepository;
    private final JwtTokenProvider jwtTokenProvider;

    public AuthService(AuthRepository authRepository, JwtTokenProvider jwtTokenProvider) {
        this.authRepository = authRepository;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    public AuthTokenResponse login(String tenantKey, LoginRequest request) {
        String traceId = TraceGuard.requireTraceId();
        String loginId = normalizeLoginId(request.loginId());
        String password = request.password() == null ? "" : request.password();

        AuthUser user = authRepository.findActiveUserByTenantAndLoginId(tenantKey, loginId)
            .orElseThrow(() -> unauthorized("invalid_login_id"));

        if (!isValidPassword(loginId, password)) {
            throw unauthorized("invalid_password");
        }

        UserPrincipal principal = new UserPrincipal(
            user.userId().toString(),
            user.tenantId().toString(),
            user.loginId(),
            user.roles()
        );

        String accessToken = jwtTokenProvider.generateAccessToken(principal, traceId);
        String refreshToken = jwtTokenProvider.generateRefreshToken(principal, traceId);
        String refreshTokenHash = jwtTokenProvider.hashToken(refreshToken);

        Instant refreshExpiry = Instant.now().plusSeconds(1209600L);
        authRepository.saveAuthSession(
            UUID.randomUUID(),
            user.tenantId(),
            user.userId(),
            refreshTokenHash,
            refreshExpiry
        );

        return new AuthTokenResponse(
            "accepted",
            accessToken,
            refreshToken,
            user.userId().toString(),
            user.tenantId().toString(),
            user.roles(),
            traceId
        );
    }

    public AuthTokenResponse refresh(String tenantKey, RefreshRequest request) {
        String traceId = TraceGuard.requireTraceId();

        Claims claims = parseToken(request.refreshToken());
        validateTokenType(claims, "refresh");

        String refreshHash = jwtTokenProvider.hashToken(request.refreshToken());
        if (!authRepository.existsValidSessionByTokenHash(refreshHash)) {
            throw unauthorized("session_not_found");
        }

        String tokenTenantId = claims.get("tenant_id", String.class);
        AuthUser user = authRepository.findActiveUserById(UUID.fromString(claims.getSubject()))
            .orElseThrow(() -> unauthorized("user_not_found"));

        if (!user.tenantId().toString().equals(tokenTenantId)) {
            throw unauthorized("tenant_mismatch");
        }

        if (!user.tenantKey().equals(tenantKey)) {
            throw unauthorized("tenant_key_mismatch");
        }

        UserPrincipal principal = new UserPrincipal(
            user.userId().toString(),
            user.tenantId().toString(),
            user.loginId(),
            user.roles()
        );

        String nextAccessToken = jwtTokenProvider.generateAccessToken(principal, traceId);
        String nextRefreshToken = jwtTokenProvider.generateRefreshToken(principal, traceId);
        String nextRefreshHash = jwtTokenProvider.hashToken(nextRefreshToken);

        authRepository.deleteSessionByTokenHash(refreshHash);
        authRepository.saveAuthSession(
            UUID.randomUUID(),
            user.tenantId(),
            user.userId(),
            nextRefreshHash,
            Instant.now().plusSeconds(1209600L)
        );

        return new AuthTokenResponse(
            "accepted",
            nextAccessToken,
            nextRefreshToken,
            user.userId().toString(),
            user.tenantId().toString(),
            user.roles(),
            traceId
        );
    }

    public void logout(LogoutRequest request) {
        String refreshHash = jwtTokenProvider.hashToken(request.refreshToken());
        authRepository.deleteSessionByTokenHash(refreshHash);
    }

    public UserPrincipal parseAccessToken(String token) {
        Claims claims = parseToken(token);
        validateTokenType(claims, "access");
        return jwtTokenProvider.toPrincipal(claims);
    }

    private Claims parseToken(String rawToken) {
        try {
            return jwtTokenProvider.parseClaims(rawToken);
        } catch (JwtException | IllegalArgumentException exception) {
            throw unauthorized("invalid_token");
        }
    }

    private void validateTokenType(Claims claims, String expectedTokenType) {
        String tokenType = claims.get("token_type", String.class);
        if (!expectedTokenType.equals(tokenType)) {
            throw unauthorized("invalid_token_type");
        }
    }

    private ApiException unauthorized(String detail) {
        return new ApiException(
            HttpStatus.UNAUTHORIZED,
            "SEC-001-401",
            ErrorCatalog.messageOf("SEC-001-401"),
            List.of(detail)
        );
    }

    private String normalizeLoginId(String loginId) {
        if (loginId == null || loginId.isBlank()) {
            return "agent1";
        }
        return loginId.trim();
    }

    private boolean isValidPassword(String loginId, String password) {
        String expectedPassword = MVP_PASSWORDS.get(loginId);
        return expectedPassword != null && expectedPassword.equals(password);
    }
}
