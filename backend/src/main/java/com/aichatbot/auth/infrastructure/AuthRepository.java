package com.aichatbot.auth.infrastructure;

import com.aichatbot.auth.domain.AuthUser;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AuthRepository {

    private final JdbcTemplate jdbcTemplate;

    public AuthRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<AuthUser> findActiveUserByTenantAndLoginId(String tenantKey, String loginId) {
        List<AuthUser> users = jdbcTemplate.query(
            """
            SELECT u.id AS user_id,
                   u.tenant_id AS tenant_id,
                   t.tenant_key AS tenant_key,
                   u.login_id AS login_id,
                   u.display_name AS display_name
            FROM tb_user u
            JOIN tb_tenant t ON t.id = u.tenant_id
            WHERE t.tenant_key = ?
              AND t.status = 'active'
              AND u.login_id = ?
              AND u.status = 'active'
            """,
            (rs, rowNum) -> new AuthUser(
                UUID.fromString(rs.getString("user_id")),
                UUID.fromString(rs.getString("tenant_id")),
                rs.getString("tenant_key"),
                rs.getString("login_id"),
                rs.getString("display_name"),
                List.of()
            ),
            tenantKey,
            loginId
        );

        if (users.isEmpty()) {
            return Optional.empty();
        }

        AuthUser user = users.get(0);
        List<String> roles = findRolesByUserId(user.userId());
        return Optional.of(new AuthUser(
            user.userId(),
            user.tenantId(),
            user.tenantKey(),
            user.loginId(),
            user.displayName(),
            roles
        ));
    }

    public Optional<AuthUser> findActiveUserById(UUID userId) {
        List<AuthUser> users = jdbcTemplate.query(
            """
            SELECT u.id AS user_id,
                   u.tenant_id AS tenant_id,
                   t.tenant_key AS tenant_key,
                   u.login_id AS login_id,
                   u.display_name AS display_name
            FROM tb_user u
            JOIN tb_tenant t ON t.id = u.tenant_id
            WHERE u.id = ?
              AND t.status = 'active'
              AND u.status = 'active'
            """,
            (rs, rowNum) -> new AuthUser(
                UUID.fromString(rs.getString("user_id")),
                UUID.fromString(rs.getString("tenant_id")),
                rs.getString("tenant_key"),
                rs.getString("login_id"),
                rs.getString("display_name"),
                List.of()
            ),
            userId
        );

        if (users.isEmpty()) {
            return Optional.empty();
        }

        AuthUser user = users.get(0);
        List<String> roles = findRolesByUserId(user.userId());
        return Optional.of(new AuthUser(
            user.userId(),
            user.tenantId(),
            user.tenantKey(),
            user.loginId(),
            user.displayName(),
            roles
        ));
    }

    public List<String> findRolesByUserId(UUID userId) {
        return jdbcTemplate.query(
            """
            SELECT r.role_code
            FROM tb_user_role ur
            JOIN tb_role r ON r.id = ur.role_id
            WHERE ur.user_id = ?
            ORDER BY r.role_code
            """,
            (rs, rowNum) -> rs.getString("role_code"),
            userId
        );
    }

    public void saveAuthSession(UUID id, UUID tenantId, UUID userId, String tokenHash, Instant expiresAt) {
        jdbcTemplate.update(
            """
            INSERT INTO tb_auth_session(id, tenant_id, user_id, session_token_hash, expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            id,
            tenantId,
            userId,
            tokenHash,
            Timestamp.from(expiresAt)
        );
    }

    public boolean existsValidSessionByTokenHash(String tokenHash) {
        Integer count = jdbcTemplate.queryForObject(
            """
            SELECT COUNT(1)
            FROM tb_auth_session
            WHERE session_token_hash = ?
              AND expires_at >= CURRENT_TIMESTAMP
            """,
            Integer.class,
            tokenHash
        );
        return count != null && count > 0;
    }

    public void deleteSessionByTokenHash(String tokenHash) {
        jdbcTemplate.update(
            """
            DELETE FROM tb_auth_session
            WHERE session_token_hash = ?
            """,
            tokenHash
        );
    }
}
