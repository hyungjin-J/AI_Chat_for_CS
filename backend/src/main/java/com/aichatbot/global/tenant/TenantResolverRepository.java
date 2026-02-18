package com.aichatbot.global.tenant;

import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class TenantResolverRepository {

    private final JdbcTemplate jdbcTemplate;

    public TenantResolverRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<UUID> findTenantIdByKey(String tenantKey) {
        return jdbcTemplate.query(
            """
            SELECT id
            FROM tb_tenant
            WHERE tenant_key = ?
              AND status = 'active'
            """,
            rs -> {
                if (rs.next()) {
                    return Optional.of(UUID.fromString(rs.getString("id")));
                }
                return Optional.empty();
            },
            tenantKey
        );
    }
}
