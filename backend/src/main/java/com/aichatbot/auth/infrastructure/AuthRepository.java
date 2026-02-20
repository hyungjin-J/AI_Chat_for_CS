package com.aichatbot.auth.infrastructure;

import com.aichatbot.auth.domain.AuthUser;
import com.aichatbot.auth.domain.AuthUserProjection;
import com.aichatbot.auth.domain.mapper.AuthMapper;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

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

        List<String> roles = findRolesByUserId(UUID.fromString(user.userId()));
        return Optional.of(new AuthUser(
            UUID.fromString(user.userId()),
            UUID.fromString(user.tenantId()),
            user.tenantKey(),
            user.loginId(),
            user.displayName(),
            roles
        ));
    }

    public Optional<AuthUser> findActiveUserById(UUID userId) {
        AuthUserProjection user = authMapper.findActiveUserById(userId);
        if (user == null) {
            return Optional.empty();
        }

        List<String> roles = findRolesByUserId(UUID.fromString(user.userId()));
        return Optional.of(new AuthUser(
            UUID.fromString(user.userId()),
            UUID.fromString(user.tenantId()),
            user.tenantKey(),
            user.loginId(),
            user.displayName(),
            roles
        ));
    }

    public List<String> findRolesByUserId(UUID userId) {
        return authMapper.findRolesByUserId(userId);
    }

    public void saveAuthSession(UUID id, UUID tenantId, UUID userId, String tokenHash, Instant expiresAt) {
        authMapper.saveAuthSession(id, tenantId, userId, tokenHash, expiresAt);
    }

    public boolean existsValidSessionByTokenHash(String tokenHash) {
        Integer count = authMapper.countValidSessionByTokenHash(tokenHash);
        return count != null && count > 0;
    }

    public void deleteSessionByTokenHash(String tokenHash) {
        authMapper.deleteSessionByTokenHash(tokenHash);
    }
}
