package com.aichatbot.auth.presentation;

import com.aichatbot.auth.application.AuthPolicyService;
import com.aichatbot.auth.application.AuthService;
import com.aichatbot.auth.domain.AuthSessionOverview;
import com.aichatbot.auth.presentation.dto.AuthTokenResponse;
import com.aichatbot.auth.presentation.dto.LoginRequest;
import com.aichatbot.auth.presentation.dto.LogoutRequest;
import com.aichatbot.auth.presentation.dto.RefreshRequest;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.idempotency.IdempotencyService;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.time.Duration;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final IdempotencyService idempotencyService;
    private final AppProperties appProperties;
    private final AuthPolicyService authPolicyService;

    public AuthController(
        AuthService authService,
        IdempotencyService idempotencyService,
        AppProperties appProperties,
        AuthPolicyService authPolicyService
    ) {
        this.authService = authService;
        this.idempotencyService = idempotencyService;
        this.appProperties = appProperties;
        this.authPolicyService = authPolicyService;
    }

    @PostMapping("/login")
    public ResponseEntity<AuthTokenResponse> login(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody LoginRequest request,
        HttpServletRequest httpRequest
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        AuthService.AuthIssue issue = idempotencyService.execute(
            "auth:login:" + TenantContext.getTenantKey(),
            key,
            () -> authService.login(TenantContext.getTenantKey(), request, resolveClientIp(httpRequest))
        );
        ResponseEntity.BodyBuilder builder = ResponseEntity.status(issue.status());
        if (issue.refreshCookieIssued()) {
            builder.header(HttpHeaders.SET_COOKIE, buildRefreshCookie(issue.refreshToken(), false).toString());
        }
        return builder.body(issue.response());
    }

    @PostMapping("/refresh")
    public ResponseEntity<AuthTokenResponse> refresh(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @RequestHeader(value = "Origin", required = false) String originHeader,
        @Valid @RequestBody RefreshRequest request,
        HttpServletRequest httpRequest
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        authPolicyService.validateCsrfOrigin(originHeader, request.clientType());
        ResolvedRefreshToken resolved = resolveRefreshToken(httpRequest, request.refreshToken(), request.clientType());

        AuthService.AuthIssue issue = idempotencyService.execute(
            "auth:refresh:" + TenantContext.getTenantKey(),
            key,
            () -> authService.refresh(
                TenantContext.getTenantKey(),
                resolved.refreshToken(),
                request.clientType(),
                resolveClientIp(httpRequest),
                resolved.fromBodyFallback()
            )
        );
        return ResponseEntity.status(issue.status())
            .header(HttpHeaders.SET_COOKIE, buildRefreshCookie(issue.refreshToken(), false).toString())
            .body(issue.response());
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @RequestHeader(value = "Origin", required = false) String originHeader,
        @Valid @RequestBody LogoutRequest request,
        HttpServletRequest httpRequest
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        authPolicyService.validateCsrfOrigin(originHeader, request.clientType());
        ResolvedRefreshToken resolved = resolveRefreshToken(httpRequest, request.refreshToken(), request.clientType());

        idempotencyService.execute(
            "auth:logout:" + TenantContext.getTenantKey(),
            key,
            () -> {
                authService.logout(resolved.refreshToken(), request.reason());
                return new LogoutResult("accepted");
            }
        );
        return ResponseEntity.status(HttpStatus.CREATED)
            .header(HttpHeaders.SET_COOKIE, buildRefreshCookie("", true).toString())
            .body(new LogoutResult("accepted"));
    }

    @PostMapping("/mfa/totp/enroll")
    public MfaEnrollResponse enrollTotp(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody MfaEnrollRequest request
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UUID challengeId = parseRequiredUuid(request.mfaTicketId(), "invalid_mfa_ticket_id");
        AuthService.MfaEnrollResult result = idempotencyService.execute(
            "auth:mfa:enroll:" + TenantContext.getTenantKey(),
            key,
            () -> authService.enrollTotp(TenantContext.getTenantKey(), challengeId)
        );
        return new MfaEnrollResponse(
            result.result(),
            result.mfaTicketId(),
            result.totpSecret(),
            result.otpauthUri(),
            result.traceId()
        );
    }

    @PostMapping("/mfa/totp/activate")
    public ResponseEntity<AuthTokenResponse> activateTotp(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody MfaActivateRequest request,
        HttpServletRequest httpRequest
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UUID challengeId = parseRequiredUuid(request.mfaTicketId(), "invalid_mfa_ticket_id");
        AuthService.AuthIssue issue = idempotencyService.execute(
            "auth:mfa:activate:" + TenantContext.getTenantKey(),
            key,
            () -> authService.activateTotp(
                TenantContext.getTenantKey(),
                challengeId,
                request.totpCode(),
                request.clientType(),
                resolveClientIp(httpRequest)
            )
        );
        return ResponseEntity.status(issue.status())
            .header(HttpHeaders.SET_COOKIE, buildRefreshCookie(issue.refreshToken(), false).toString())
            .body(issue.response());
    }

    @PostMapping("/mfa/verify")
    public ResponseEntity<AuthTokenResponse> verifyMfa(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody MfaVerifyRequest request,
        HttpServletRequest httpRequest
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UUID challengeId = parseRequiredUuid(request.mfaTicketId(), "invalid_mfa_ticket_id");
        AuthService.AuthIssue issue = idempotencyService.execute(
            "auth:mfa:verify:" + TenantContext.getTenantKey(),
            key,
            () -> authService.verifyMfa(
                TenantContext.getTenantKey(),
                challengeId,
                request.totpCode(),
                request.recoveryCode(),
                request.clientType(),
                resolveClientIp(httpRequest)
            )
        );
        return ResponseEntity.status(issue.status())
            .header(HttpHeaders.SET_COOKIE, buildRefreshCookie(issue.refreshToken(), false).toString())
            .body(issue.response());
    }

    @PostMapping("/mfa/recovery-codes/regenerate")
    public RecoveryCodesResponse regenerateRecoveryCodes(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        List<String> recoveryCodes = idempotencyService.execute(
            "auth:mfa:recovery:" + TenantContext.getTenantKey(),
            key,
            () -> authService.regenerateRecoveryCodes(principal)
        );
        return new RecoveryCodesResponse("accepted", recoveryCodes);
    }

    @GetMapping("/sessions")
    public SessionListResponse listSessions() {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        List<AuthSessionOverview> sessions = authService.listActiveSessions(principal);
        List<SessionItem> items = sessions.stream()
            .map(session -> new SessionItem(
                session.sessionId().toString(),
                session.createdAt(),
                session.lastSeenAt(),
                session.expiresAt(),
                session.clientType(),
                session.deviceName(),
                session.createdIp(),
                session.consumedIp()
            ))
            .toList();
        return new SessionListResponse(items);
    }

    @DeleteMapping("/sessions/{session_id}")
    public SessionMutationResponse revokeSession(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @PathVariable("session_id") String sessionId,
        @RequestParam(value = "current_session_id", required = false) String currentSessionId
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID targetSessionId = parseRequiredUuid(sessionId, "invalid_session_id");
        UUID currentFamilyId = parseUuidOrNull(currentSessionId);
        idempotencyService.execute(
            "auth:sessions:revoke:" + TenantContext.getTenantKey(),
            key,
            () -> {
                authService.revokeSession(principal, targetSessionId, currentFamilyId);
                return Boolean.TRUE;
            }
        );
        return new SessionMutationResponse("accepted");
    }

    @PostMapping("/sessions/revoke-others")
    public SessionMutationResponse revokeOtherSessions(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody RevokeOthersRequest request
    ) {
        String key = requireIdempotencyKey(idempotencyKey);
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        UUID currentFamilyId = parseRequiredUuid(request.currentSessionId(), "current_session_id_required");
        idempotencyService.execute(
            "auth:sessions:revoke-others:" + TenantContext.getTenantKey(),
            key,
            () -> {
                authService.revokeOtherSessions(principal, currentFamilyId);
                return Boolean.TRUE;
            }
        );
        return new SessionMutationResponse("accepted");
    }

    private String requireIdempotencyKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("idempotency_key_required")
            );
        }
        return idempotencyKey.trim();
    }

    private ResolvedRefreshToken resolveRefreshToken(HttpServletRequest request, String bodyRefreshToken, String clientType) {
        String cookieToken = readCookieValue(request, appProperties.getAuth().getRefreshCookieName());
        if (cookieToken != null && !cookieToken.isBlank()) {
            return new ResolvedRefreshToken(cookieToken, false);
        }

        if (bodyRefreshToken != null && !bodyRefreshToken.isBlank()) {
            if (!authPolicyService.isRefreshBodyFallbackAllowed(clientType)) {
                throw new ApiException(
                    HttpStatus.UNPROCESSABLE_ENTITY,
                    "API-003-422",
                    ErrorCatalog.messageOf("API-003-422"),
                    List.of("refresh_body_fallback_disallowed")
                );
            }
            return new ResolvedRefreshToken(bodyRefreshToken, true);
        }

        throw new ApiException(
            HttpStatus.UNPROCESSABLE_ENTITY,
            "API-003-422",
            ErrorCatalog.messageOf("API-003-422"),
            List.of("refresh_token_missing")
        );
    }

    private String readCookieValue(HttpServletRequest request, String cookieName) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null || cookies.length == 0) {
            return null;
        }
        return Arrays.stream(cookies)
            .filter(cookie -> cookieName.equals(cookie.getName()))
            .map(Cookie::getValue)
            .findFirst()
            .orElse(null);
    }

    private String resolveClientIp(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            return forwardedFor.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return realIp.trim();
        }
        return request.getRemoteAddr();
    }

    private UUID parseRequiredUuid(String rawValue, String detail) {
        try {
            return UUID.fromString(rawValue);
        } catch (Exception exception) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of(detail)
            );
        }
    }

    private UUID parseUuidOrNull(String rawValue) {
        if (rawValue == null || rawValue.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(rawValue);
        } catch (Exception exception) {
            return null;
        }
    }

    private ResponseCookie buildRefreshCookie(String value, boolean clear) {
        Duration maxAge = clear
            ? Duration.ZERO
            : Duration.ofSeconds(appProperties.getJwt().getRefreshExpirationSec());
        return ResponseCookie.from(appProperties.getAuth().getRefreshCookieName(), value)
            .httpOnly(true)
            .secure(appProperties.getAuth().isRefreshCookieSecure() || authPolicyService.isProdMode())
            .sameSite(appProperties.getAuth().getSameSite())
            .path(appProperties.getAuth().getRefreshCookiePath())
            .maxAge(maxAge)
            .build();
    }

    private record LogoutResult(String result) {
    }

    private record ResolvedRefreshToken(String refreshToken, boolean fromBodyFallback) {
    }

    private record MfaEnrollRequest(
        @NotBlank
        String mfaTicketId
    ) {
    }

    private record MfaEnrollResponse(
        String result,
        String mfaTicketId,
        String totpSecret,
        String otpauthUri,
        String traceId
    ) {
    }

    private record MfaActivateRequest(
        @NotBlank
        String mfaTicketId,
        @NotBlank
        String totpCode,
        String clientType
    ) {
    }

    private record MfaVerifyRequest(
        @NotBlank
        String mfaTicketId,
        String totpCode,
        String recoveryCode,
        String clientType
    ) {
    }

    private record RecoveryCodesResponse(
        String result,
        List<String> recoveryCodes
    ) {
    }

    private record SessionListResponse(
        List<SessionItem> items
    ) {
    }

    private record SessionItem(
        String sessionId,
        java.time.Instant createdAt,
        java.time.Instant lastSeenAt,
        java.time.Instant expiresAt,
        String clientType,
        String deviceName,
        String createdIp,
        String consumedIp
    ) {
    }

    private record RevokeOthersRequest(
        @NotBlank
        String currentSessionId
    ) {
    }

    private record SessionMutationResponse(String result) {
    }
}
