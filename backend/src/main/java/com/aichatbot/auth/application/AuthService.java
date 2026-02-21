package com.aichatbot.auth.application;

import com.aichatbot.auth.domain.AuthSessionOverview;
import com.aichatbot.auth.domain.AuthSessionRecord;
import com.aichatbot.auth.domain.AuthUser;
import com.aichatbot.auth.domain.MfaChallengeRecord;
import com.aichatbot.auth.domain.UserMfaRecord;
import com.aichatbot.auth.infrastructure.AuthMfaRepository;
import com.aichatbot.auth.infrastructure.AuthRepository;
import com.aichatbot.auth.presentation.dto.AuthTokenResponse;
import com.aichatbot.auth.presentation.dto.LoginRequest;
import com.aichatbot.global.audit.AuditLogService;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.error.RetryAfterApiException;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.ops.application.OpsBlockService;
import com.aichatbot.ops.application.OpsEventService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

    private static final Map<String, String> MVP_PASSWORDS = Map.of(
        "agent1", "agent1-pass",
        "admin1", "admin1-pass",
        "admin2", "admin2-pass",
        "admin3", "admin3-pass",
        "ops1", "ops1-pass"
    );

    private final AuthRepository authRepository;
    private final AuthMfaRepository authMfaRepository;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuthRateLimitService authRateLimitService;
    private final AuditLogService auditLogService;
    private final OpsEventService opsEventService;
    private final OpsBlockService opsBlockService;
    private final AppProperties appProperties;
    private final TotpService totpService;
    private final MfaSecretCryptoService mfaSecretCryptoService;
    private final Clock clock;

    @Autowired
    public AuthService(
        AuthRepository authRepository,
        AuthMfaRepository authMfaRepository,
        JwtTokenProvider jwtTokenProvider,
        AuthRateLimitService authRateLimitService,
        AuditLogService auditLogService,
        OpsEventService opsEventService,
        OpsBlockService opsBlockService,
        AppProperties appProperties,
        TotpService totpService,
        MfaSecretCryptoService mfaSecretCryptoService
    ) {
        this(
            authRepository,
            authMfaRepository,
            jwtTokenProvider,
            authRateLimitService,
            auditLogService,
            opsEventService,
            opsBlockService,
            appProperties,
            totpService,
            mfaSecretCryptoService,
            Clock.systemUTC()
        );
    }

    AuthService(
        AuthRepository authRepository,
        AuthMfaRepository authMfaRepository,
        JwtTokenProvider jwtTokenProvider,
        AuthRateLimitService authRateLimitService,
        AuditLogService auditLogService,
        OpsEventService opsEventService,
        OpsBlockService opsBlockService,
        AppProperties appProperties,
        TotpService totpService,
        MfaSecretCryptoService mfaSecretCryptoService,
        Clock clock
    ) {
        this.authRepository = authRepository;
        this.authMfaRepository = authMfaRepository;
        this.jwtTokenProvider = jwtTokenProvider;
        this.authRateLimitService = authRateLimitService;
        this.auditLogService = auditLogService;
        this.opsEventService = opsEventService;
        this.opsBlockService = opsBlockService;
        this.appProperties = appProperties;
        this.totpService = totpService;
        this.mfaSecretCryptoService = mfaSecretCryptoService;
        this.clock = clock;
    }

    @Transactional(noRollbackFor = ApiException.class)
    public AuthIssue login(String tenantKey, LoginRequest request, String clientIp) {
        String traceId = TraceGuard.requireTraceId();
        Instant now = Instant.now(clock);
        String loginId = normalizeLoginId(request.loginId());
        String password = request.password() == null ? "" : request.password();
        String clientType = normalizeClientType(request.clientType());
        UUID tenantId = UUID.fromString(com.aichatbot.global.tenant.TenantContext.getTenantId());

        AuthRateLimitService.RateLimitDecision rateDecision =
            authRateLimitService.consumeLoginAttempt(tenantKey, normalizeIp(clientIp));
        if (!rateDecision.allowed()) {
            opsEventService.append(tenantId, "AUTH_RATE_LIMITED", "auth_rate_limited", 1L, Map.of("tenant_key", tenantKey, "ip", normalizeIp(clientIp)));
            throw new RetryAfterApiException(
                HttpStatus.TOO_MANY_REQUESTS,
                "AUTH_RATE_LIMITED",
                ErrorCatalog.messageOf("AUTH_RATE_LIMITED"),
                List.of("login_rate_limited"),
                rateDecision.retryAfterSeconds(),
                rateDecision.limit(),
                rateDecision.remaining(),
                rateDecision.resetEpochSeconds()
            );
        }

        AuthUser user = authRepository.findActiveUserByTenantAndLoginId(tenantKey, loginId)
            .orElseThrow(() -> unauthorized("invalid_login_id"));

        if (opsBlockService.findActive(user.tenantId(), "ACCOUNT", user.loginId()).isPresent()
            || opsBlockService.findActive(user.tenantId(), "IP", normalizeIp(clientIp)).isPresent()) {
            throw new ApiException(HttpStatus.FORBIDDEN, "SEC-002-403", ErrorCatalog.messageOf("SEC-002-403"), List.of("blocked_account_or_ip"));
        }

        if (user.lockedUntil() != null) {
            int cleared = authRepository.clearExpiredLock(user.userId());
            if (cleared <= 0) {
                throw lockoutException(Math.max(1L, ChronoUnit.SECONDS.between(now, user.lockedUntil())));
            }
            user = authRepository.findActiveUserById(user.userId()).orElseThrow(() -> unauthorized("user_not_found_after_unlock"));
        }

        if (!isValidPassword(loginId, password)) {
            int nextFailedCount = user.failedLoginCount() + 1;
            Instant lockUntil = now.plus(appProperties.getAuth().getLockoutMinutes(), ChronoUnit.MINUTES);
            authRepository.incrementFailedLogin(user.userId(), now, lockUntil, appProperties.getAuth().getLockoutThreshold());
            opsEventService.append(user.tenantId(), "AUTH_LOGIN_FAILED", "auth_login_failed", 1L, Map.of("login_id", loginId));
            if (nextFailedCount >= appProperties.getAuth().getLockoutThreshold()) {
                throw lockoutException(Math.max(1L, appProperties.getAuth().getLockoutMinutes() * 60L));
            }
            throw unauthorized("invalid_password");
        }

        authRepository.resetFailedLogin(user.userId());

        if (requiresMfa(user)) {
            UUID challengeId = authMfaRepository.createChallenge(
                user.tenantId(),
                user.userId(),
                user.mfaEnabled() ? "VERIFY_REQUIRED" : "SETUP_REQUIRED",
                now.plus(appProperties.getAuth().getMfaChallengeTtlMinutes(), ChronoUnit.MINUTES),
                UUID.fromString(traceId)
            );
            String mfaStatus = user.mfaEnabled() ? "mfa_required" : "mfa_setup_required";
            AuthTokenResponse response = new AuthTokenResponse(
                mfaStatus, null, null, null, challengeId.toString(), mfaStatus,
                user.userId().toString(), user.tenantId().toString(), user.roles(), user.permissionVersion(), user.adminLevel(), List.of(), traceId
            );
            return new AuthIssue(response, null, false, HttpStatus.ACCEPTED);
        }

        return issueTokens(user, clientType, clientIp, traceId, List.of());
    }

    @Transactional(noRollbackFor = ApiException.class)
    public AuthIssue refresh(String tenantKey, String refreshToken, String clientType, String clientIp, boolean bodyFallbackUsed) {
        String traceId = TraceGuard.requireTraceId();
        Instant now = Instant.now(clock);
        Claims claims = parseToken(refreshToken);
        validateTokenType(claims, "refresh");
        UUID userId = UUID.fromString(claims.getSubject());
        UUID tenantId = UUID.fromString(claims.get("tenant_id", String.class));
        UUID sessionFamilyId = UUID.fromString(claims.get("session_family_id", String.class));
        String refreshJti = claims.getId();
        String refreshHash = jwtTokenProvider.hashToken(refreshToken);

        if (authRepository.consumeRefreshSessionByTokenHash(refreshHash, now, normalizeIp(clientIp)) != 1) {
            authRepository.revokeSessionFamily(sessionFamilyId, now, "refresh_reuse_detected");
            throw new ApiException(HttpStatus.CONFLICT, "AUTH_REFRESH_REUSE_DETECTED", ErrorCatalog.messageOf("AUTH_REFRESH_REUSE_DETECTED"), List.of("refresh_reuse_detected"));
        }

        AuthUser user = authRepository.findActiveUserById(userId).orElseThrow(() -> unauthorized("user_not_found"));
        if (!user.tenantId().equals(tenantId) || !user.tenantKey().equals(tenantKey)) {
            throw unauthorized("tenant_mismatch");
        }

        UserPrincipal principal = toPrincipal(user);
        UUID nextRefreshJti = UUID.randomUUID();
        String nextAccessToken = jwtTokenProvider.generateAccessToken(principal, traceId, sessionFamilyId);
        String nextRefreshToken = jwtTokenProvider.generateRefreshToken(principal, traceId, nextRefreshJti, sessionFamilyId);
        authRepository.insertAuthSession(
            UUID.randomUUID(), tenantId, userId, sessionFamilyId,
            jwtTokenProvider.hashToken(nextRefreshToken), jwtTokenProvider.hashJti(nextRefreshJti.toString()), jwtTokenProvider.hashJti(refreshJti),
            now.plusSeconds(appProperties.getJwt().getRefreshExpirationSec()), normalizeClientType(clientType), normalizeIp(clientIp), UUID.fromString(traceId)
        );

        if (bodyFallbackUsed) {
            auditLogService.write(tenantId, "AUTH_REFRESH_FALLBACK_USED", userId, String.join(",", user.roles()), "AUTH_SESSION", sessionFamilyId.toString(), Map.of("client_type", clientType), Map.of("source", "request_body"));
        }

        AuthTokenResponse response = new AuthTokenResponse(
            "accepted", nextAccessToken, nextRefreshToken, sessionFamilyId.toString(), null, null,
            user.userId().toString(), user.tenantId().toString(), user.roles(), user.permissionVersion(), user.adminLevel(), List.of(), traceId
        );
        return new AuthIssue(response, nextRefreshToken, true, HttpStatus.CREATED);
    }

    @Transactional
    public void logout(String refreshToken, String reason) {
        Instant now = Instant.now(clock);
        String tokenHash = jwtTokenProvider.hashToken(refreshToken);
        AuthSessionRecord existing = authRepository.findSessionByTokenHash(tokenHash).orElse(null);
        authRepository.revokeSessionByTokenHash(tokenHash, now, reason == null ? "logout" : reason);
        if (existing != null) {
            authRepository.revokeSessionFamily(existing.sessionFamilyId(), now, "logout");
            auditLogService.write(
                existing.tenantId(),
                "AUTH_LOGOUT",
                existing.userId(),
                "AUTH",
                "AUTH_SESSION_FAMILY",
                existing.sessionFamilyId().toString(),
                Map.of("token_hash", tokenHash),
                Map.of("result", "revoked")
            );
        }
    }

    @Transactional(noRollbackFor = ApiException.class)
    public MfaEnrollResult enrollTotp(String tenantKey, UUID challengeId) {
        String traceId = TraceGuard.requireTraceId();
        Instant now = Instant.now(clock);
        UUID tenantId = UUID.fromString(com.aichatbot.global.tenant.TenantContext.getTenantId());
        MfaChallengeRecord challenge = requireActiveChallenge(tenantId, challengeId, "SETUP_REQUIRED", now);
        AuthUser user = authRepository.findActiveUserById(challenge.userId()).orElseThrow(() -> unauthorized("user_not_found"));
        if (!user.tenantKey().equals(tenantKey)) {
            throw unauthorized("tenant_mismatch");
        }

        String secretBase32 = totpService.generateSecretBase32();
        authMfaRepository.setChallengeSecret(tenantId, challengeId, mfaSecretCryptoService.encrypt(secretBase32), now);
        return new MfaEnrollResult(
            "mfa_enroll_ready",
            challengeId.toString(),
            secretBase32,
            totpService.buildOtpAuthUri(appProperties.getAuth().getMfaIssuer(), user.loginId(), secretBase32),
            traceId
        );
    }

    @Transactional(noRollbackFor = ApiException.class)
    public AuthIssue activateTotp(String tenantKey, UUID challengeId, String totpCode, String clientType, String clientIp) {
        String traceId = TraceGuard.requireTraceId();
        Instant now = Instant.now(clock);
        UUID tenantId = UUID.fromString(com.aichatbot.global.tenant.TenantContext.getTenantId());
        MfaChallengeRecord challenge = requireActiveChallenge(tenantId, challengeId, "SETUP_REQUIRED", now);
        if (challenge.totpSecretCiphertext() == null || challenge.totpSecretCiphertext().isBlank()) {
            throw new ApiException(HttpStatus.CONFLICT, "AUTH_MFA_SETUP_REQUIRED", ErrorCatalog.messageOf("AUTH_MFA_SETUP_REQUIRED"), List.of("totp_secret_not_enrolled"));
        }

        String secret = mfaSecretCryptoService.decrypt(challenge.totpSecretCiphertext());
        if (!totpService.verifyCode(secret, normalizeTotpCode(totpCode), now)) {
            handleMfaFailure(challenge, now);
        }

        AuthUser user = authRepository.findActiveUserById(challenge.userId()).orElseThrow(() -> unauthorized("user_not_found"));
        if (!user.tenantKey().equals(tenantKey)) {
            throw unauthorized("tenant_mismatch");
        }

        authMfaRepository.upsertUserMfa(
            UUID.randomUUID(),
            user.tenantId(),
            user.userId(),
            "TOTP",
            challenge.totpSecretCiphertext(),
            true,
            true,
            now,
            now
        );

        List<String> recoveryCodes = totpService.generateRecoveryCodes(appProperties.getAuth().getMfaRecoveryCodeCount());
        List<String> codeHashes = recoveryCodes.stream().map(totpService::hashRecoveryCode).toList();
        authMfaRepository.replaceRecoveryCodes(
            user.tenantId(),
            user.userId(),
            codeHashes,
            now.plus(appProperties.getAuth().getMfaRecoveryCodeTtlDays(), ChronoUnit.DAYS)
        );
        authMfaRepository.consumeChallenge(tenantId, challengeId, now);
        return issueTokens(user, clientType, clientIp, traceId, recoveryCodes);
    }

    @Transactional(noRollbackFor = ApiException.class)
    public AuthIssue verifyMfa(String tenantKey, UUID challengeId, String totpCode, String recoveryCode, String clientType, String clientIp) {
        String traceId = TraceGuard.requireTraceId();
        Instant now = Instant.now(clock);
        UUID tenantId = UUID.fromString(com.aichatbot.global.tenant.TenantContext.getTenantId());
        MfaChallengeRecord challenge = requireActiveChallenge(tenantId, challengeId, "VERIFY_REQUIRED", now);

        if (challenge.lockedUntil() != null && challenge.lockedUntil().isAfter(now)) {
            long retryAfter = Math.max(1L, ChronoUnit.SECONDS.between(now, challenge.lockedUntil()));
            throw new RetryAfterApiException(
                HttpStatus.TOO_MANY_REQUESTS,
                "AUTH_MFA_LOCKED",
                ErrorCatalog.messageOf("AUTH_MFA_LOCKED"),
                List.of("mfa_locked"),
                retryAfter,
                null,
                null,
                null
            );
        }

        AuthUser user = authRepository.findActiveUserById(challenge.userId()).orElseThrow(() -> unauthorized("user_not_found"));
        if (!user.tenantKey().equals(tenantKey)) {
            throw unauthorized("tenant_mismatch");
        }

        UserMfaRecord mfaRecord = authMfaRepository.findByUserId(user.userId())
            .orElseThrow(() -> new ApiException(
                HttpStatus.UNAUTHORIZED,
                "AUTH_MFA_SETUP_REQUIRED",
                ErrorCatalog.messageOf("AUTH_MFA_SETUP_REQUIRED"),
                List.of("mfa_not_configured")
            ));

        boolean verified;
        if (recoveryCode != null && !recoveryCode.isBlank()) {
            verified = authMfaRepository.consumeRecoveryCode(user.tenantId(), user.userId(), totpService.hashRecoveryCode(recoveryCode), now);
        } else {
            verified = totpService.verifyCode(mfaSecretCryptoService.decrypt(mfaRecord.secretCiphertext()), normalizeTotpCode(totpCode), now);
        }
        if (!verified) {
            handleMfaFailure(challenge, now);
        }

        authMfaRepository.consumeChallenge(tenantId, challengeId, now);
        return issueTokens(user, clientType, clientIp, traceId, List.of());
    }

    @Transactional
    public List<String> regenerateRecoveryCodes(UserPrincipal principal) {
        Instant now = Instant.now(clock);
        UUID tenantId = UUID.fromString(principal.tenantId());
        UUID userId = UUID.fromString(principal.userId());
        UserMfaRecord mfaRecord = authMfaRepository.findByUserId(userId)
            .orElseThrow(() -> new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "AUTH_MFA_SETUP_REQUIRED",
                ErrorCatalog.messageOf("AUTH_MFA_SETUP_REQUIRED"),
                List.of("mfa_not_configured")
            ));
        if (!mfaRecord.enabled()) {
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "AUTH_MFA_SETUP_REQUIRED", ErrorCatalog.messageOf("AUTH_MFA_SETUP_REQUIRED"), List.of("mfa_not_enabled"));
        }
        List<String> recoveryCodes = totpService.generateRecoveryCodes(appProperties.getAuth().getMfaRecoveryCodeCount());
        authMfaRepository.replaceRecoveryCodes(
            tenantId,
            userId,
            recoveryCodes.stream().map(totpService::hashRecoveryCode).toList(),
            now.plus(appProperties.getAuth().getMfaRecoveryCodeTtlDays(), ChronoUnit.DAYS)
        );
        return recoveryCodes;
    }

    public List<AuthSessionOverview> listActiveSessions(UserPrincipal principal) {
        return authRepository.findActiveSessionsByUser(
            UUID.fromString(principal.tenantId()),
            UUID.fromString(principal.userId()),
            Instant.now(clock)
        );
    }

    @Transactional
    public void revokeSession(UserPrincipal principal, UUID sessionId, UUID currentSessionId) {
        int updated = authRepository.revokeSessionFamilyByUser(
            UUID.fromString(principal.tenantId()),
            UUID.fromString(principal.userId()),
            sessionId,
            Instant.now(clock),
            "user_session_revoke",
            currentSessionId
        );
        if (updated == 0) {
            throw new ApiException(HttpStatus.NOT_FOUND, "API-004-404", ErrorCatalog.messageOf("API-004-404"), List.of("session_not_found"));
        }
    }

    @Transactional
    public void revokeOtherSessions(UserPrincipal principal, UUID currentSessionId) {
        authRepository.revokeOtherSessionFamiliesByUser(
            UUID.fromString(principal.tenantId()),
            UUID.fromString(principal.userId()),
            currentSessionId,
            Instant.now(clock),
            "user_revoke_other_sessions",
            currentSessionId
        );
    }

    public UserPrincipal parseAccessToken(String token) {
        Claims claims = parseToken(token);
        validateTokenType(claims, "access");
        return jwtTokenProvider.toPrincipal(claims);
    }

    public boolean isPermissionVersionCurrent(UserPrincipal principal) {
        long currentVersion = authRepository.findPermissionVersionByUserId(UUID.fromString(principal.userId()));
        return currentVersion == principal.permissionVersion();
    }

    private MfaChallengeRecord requireActiveChallenge(UUID tenantId, UUID challengeId, String requiredType, Instant now) {
        MfaChallengeRecord challenge = authMfaRepository.findChallenge(tenantId, challengeId)
            .orElseThrow(() -> new ApiException(
                HttpStatus.UNAUTHORIZED,
                "AUTH_MFA_CHALLENGE_INVALID",
                ErrorCatalog.messageOf("AUTH_MFA_CHALLENGE_INVALID"),
                List.of("challenge_not_found")
            ));
        if (!requiredType.equalsIgnoreCase(challenge.challengeType())) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH_MFA_CHALLENGE_INVALID", ErrorCatalog.messageOf("AUTH_MFA_CHALLENGE_INVALID"), List.of("challenge_type_mismatch"));
        }
        if (challenge.consumedAt() != null || challenge.expiresAt().isBefore(now)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH_MFA_CHALLENGE_INVALID", ErrorCatalog.messageOf("AUTH_MFA_CHALLENGE_INVALID"), List.of("challenge_expired"));
        }
        return challenge;
    }

    private void handleMfaFailure(MfaChallengeRecord challenge, Instant now) {
        authMfaRepository.incrementChallengeAttempt(challenge.tenantId(), challenge.id(), now);
        int nextAttemptCount = challenge.attemptCount() + 1;
        if (nextAttemptCount >= appProperties.getAuth().getMfaMaxAttempts()) {
            Instant lockedUntil = now.plus(appProperties.getAuth().getMfaLockMinutes(), ChronoUnit.MINUTES);
            authMfaRepository.lockChallenge(challenge.tenantId(), challenge.id(), lockedUntil, now);
            long retryAfter = Math.max(1L, ChronoUnit.SECONDS.between(now, lockedUntil));
            throw new RetryAfterApiException(
                HttpStatus.TOO_MANY_REQUESTS,
                "AUTH_MFA_LOCKED",
                ErrorCatalog.messageOf("AUTH_MFA_LOCKED"),
                List.of("mfa_locked"),
                retryAfter,
                null,
                null,
                null
            );
        }
        throw new ApiException(HttpStatus.UNAUTHORIZED, "AUTH_MFA_INVALID_CODE", ErrorCatalog.messageOf("AUTH_MFA_INVALID_CODE"), List.of("invalid_mfa_code"));
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
        return new ApiException(HttpStatus.UNAUTHORIZED, "SEC-001-401", ErrorCatalog.messageOf("SEC-001-401"), List.of(detail));
    }

    private RetryAfterApiException lockoutException(long retryAfterSeconds) {
        return new RetryAfterApiException(
            HttpStatus.TOO_MANY_REQUESTS,
            "AUTH_LOCKED",
            ErrorCatalog.messageOf("AUTH_LOCKED"),
            List.of("account_locked"),
            retryAfterSeconds,
            null,
            null,
            null
        );
    }

    private UserPrincipal toPrincipal(AuthUser user) {
        return new UserPrincipal(
            user.userId().toString(),
            user.tenantId().toString(),
            user.loginId(),
            user.roles(),
            user.permissionVersion(),
            user.adminLevel()
        );
    }

    private String normalizeLoginId(String loginId) {
        if (loginId == null || loginId.isBlank()) {
            return "agent1";
        }
        return loginId.trim();
    }

    private String normalizeClientType(String clientType) {
        if (clientType == null || clientType.isBlank()) {
            return "web";
        }
        return clientType.trim().toLowerCase(Locale.ROOT);
    }

    private Map<String, Object> singleEntryNullable(String key, Object value) {
        Map<String, Object> payload = new HashMap<>();
        payload.put(key, value);
        return payload;
    }

    private String normalizeIp(String clientIp) {
        if (clientIp == null || clientIp.isBlank()) {
            return "0.0.0.0";
        }
        return clientIp.trim();
    }

    private boolean isValidPassword(String loginId, String password) {
        String expectedPassword = MVP_PASSWORDS.get(loginId);
        return expectedPassword != null && expectedPassword.equals(password);
    }

    private String normalizeTotpCode(String code) {
        return code == null ? "" : code.replaceAll("\\s", "");
    }

    private boolean requiresMfa(AuthUser user) {
        if (!appProperties.getAuth().isMfaEnforceOpsAdmin()) {
            return false;
        }
        return user.roles().stream()
            .map(role -> role == null ? "" : role.toUpperCase(Locale.ROOT))
            .anyMatch(role -> "OPS".equals(role) || "ADMIN".equals(role));
    }

    private AuthIssue issueTokens(AuthUser user, String clientType, String clientIp, String traceId, List<String> recoveryCodes) {
        Instant now = Instant.now(clock);
        UserPrincipal principal = toPrincipal(user);
        UUID sessionFamilyId = UUID.randomUUID();
        UUID refreshJti = UUID.randomUUID();
        String accessToken = jwtTokenProvider.generateAccessToken(principal, traceId, sessionFamilyId);
        String refreshToken = jwtTokenProvider.generateRefreshToken(principal, traceId, refreshJti, sessionFamilyId);

        authRepository.insertAuthSession(
            UUID.randomUUID(),
            user.tenantId(),
            user.userId(),
            sessionFamilyId,
            jwtTokenProvider.hashToken(refreshToken),
            jwtTokenProvider.hashJti(refreshJti.toString()),
            null,
            now.plusSeconds(appProperties.getJwt().getRefreshExpirationSec()),
            normalizeClientType(clientType),
            normalizeIp(clientIp),
            UUID.fromString(traceId)
        );

        AuthTokenResponse response = new AuthTokenResponse(
            "accepted",
            accessToken,
            refreshToken,
            sessionFamilyId.toString(),
            null,
            null,
            user.userId().toString(),
            user.tenantId().toString(),
            user.roles(),
            user.permissionVersion(),
            user.adminLevel(),
            recoveryCodes == null ? List.of() : recoveryCodes,
            traceId
        );
        opsEventService.append(user.tenantId(), "AUTH_LOGIN_SUCCESS", "auth_login_success", 1L, Map.of("login_id", user.loginId()));
        return new AuthIssue(response, refreshToken, true, HttpStatus.CREATED);
    }

    public record AuthIssue(
        AuthTokenResponse response,
        String refreshToken,
        boolean refreshCookieIssued,
        HttpStatus status
    ) {
    }

    public record MfaEnrollResult(
        String result,
        String mfaTicketId,
        String totpSecret,
        String otpauthUri,
        String traceId
    ) {
    }
}
