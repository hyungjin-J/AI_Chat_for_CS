package com.aichatbot.auth.infrastructure;

import com.aichatbot.auth.domain.AuthSessionRecord;
import com.aichatbot.auth.domain.AuthSessionOverview;
import com.aichatbot.auth.domain.AuthUser;
import com.aichatbot.auth.domain.AuthUserProjection;
import com.aichatbot.auth.domain.mapper.AuthMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class AuthRepository {

    private final AuthMapper authMapper;

    public AuthRepository(AuthMapper authMapper) {
        this.authMapper = authMapper;
    }

    public Optional<AuthUser> findActiveUserByTenantAndLoginId(String tenantKey, String loginId) {
        AuthUserProjection user = authMapper.findActiveUserByTenantAndLoginId(tenantKey, loginId);
        if (user == null) {
            return Optional.empty();
        }
        List<String> roles = findRolesByUserId(user.userId());
        return Optional.of(toAuthUser(user, roles));
    }

    public Optional<AuthUser> findActiveUserById(UUID userId) {
        AuthUserProjection user = authMapper.findActiveUserById(userId);
        if (user == null) {
            return Optional.empty();
        }
        List<String> roles = findRolesByUserId(user.userId());
        return Optional.of(toAuthUser(user, roles));
    }

    public List<String> findRolesByUserId(UUID userId) {
        return authMapper.findRolesByUserId(userId);
    }

    public void insertAuthSession(
        UUID id,
        UUID tenantId,
        UUID userId,
        UUID sessionFamilyId,
        String tokenHash,
        String refreshJtiHash,
        String parentRefreshJtiHash,
        Instant expiresAt,
        String clientType,
        String createdIp,
        UUID traceId
    ) {
        authMapper.insertAuthSession(
            id,
            tenantId,
            userId,
            sessionFamilyId,
            tokenHash,
            refreshJtiHash,
            parentRefreshJtiHash,
            expiresAt,
            clientType,
            createdIp,
            traceId
        );
    }

    public Optional<AuthSessionRecord> findSessionByTokenHash(String tokenHash) {
        return Optional.ofNullable(authMapper.findSessionByTokenHash(tokenHash));
    }

    public int consumeRefreshSessionByTokenHash(String tokenHash, Instant consumedAt, String consumedIp) {
        return authMapper.consumeRefreshSessionByTokenHash(tokenHash, consumedAt, consumedIp);
    }

    public int revokeSessionFamily(UUID sessionFamilyId, Instant revokedAt, String reason) {
        return authMapper.revokeSessionFamily(sessionFamilyId, revokedAt, reason);
    }

    public int revokeSessionByTokenHash(String tokenHash, Instant revokedAt, String reason) {
        return authMapper.revokeSessionByTokenHash(tokenHash, revokedAt, reason);
    }

    public List<AuthSessionOverview> findActiveSessionsByUser(UUID tenantId, UUID userId, Instant nowUtc) {
        return authMapper.findActiveSessionsByUser(tenantId, userId, nowUtc);
    }

    public int revokeSessionFamilyByUser(UUID tenantId, UUID userId, UUID sessionFamilyId, Instant revokedAt, String reason, UUID revokedBySessionId) {
        return authMapper.revokeSessionFamilyByUser(tenantId, userId, sessionFamilyId, revokedAt, reason, revokedBySessionId);
    }

    public int revokeOtherSessionFamiliesByUser(UUID tenantId, UUID userId, UUID currentSessionFamilyId, Instant revokedAt, String reason, UUID revokedBySessionId) {
        return authMapper.revokeOtherSessionFamiliesByUser(tenantId, userId, currentSessionFamilyId, revokedAt, reason, revokedBySessionId);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void incrementFailedLogin(UUID userId, Instant failedAt, Instant lockUntil, int lockoutThreshold) {
        authMapper.incrementFailedLogin(userId, failedAt, lockUntil, lockoutThreshold);
    }

    public void resetFailedLogin(UUID userId) {
        authMapper.resetFailedLogin(userId);
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public int clearExpiredLock(UUID userId) {
        return authMapper.clearExpiredLock(userId);
    }

    public void incrementPermissionVersionByTenant(UUID tenantId) {
        authMapper.incrementPermissionVersionByTenant(tenantId);
    }

    public long findPermissionVersionByUserId(UUID userId) {
        Long value = authMapper.findPermissionVersionByUserId(userId);
        return value == null ? 0L : value;
    }

    private AuthUser toAuthUser(AuthUserProjection projection, List<String> roles) {
        return new AuthUser(
            projection.userId(),
            projection.tenantId(),
            projection.tenantKey(),
            projection.loginId(),
            projection.displayName(),
            roles,
            projection.permissionVersion(),
            projection.adminLevel(),
            projection.mfaEnabled() != null && projection.mfaEnabled(),
            projection.failedLoginCount(),
            projection.lockedUntil()
        );
    }
}
