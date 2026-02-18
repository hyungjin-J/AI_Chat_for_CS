package com.aichatbot.session.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import com.aichatbot.session.application.ConversationView;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class ConversationRepository {

    private static final UUID DEFAULT_CHANNEL_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID DEFAULT_CUSTOMER_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");

    private final JdbcTemplate jdbcTemplate;

    public ConversationRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public ConversationView create(UUID tenantId, String traceId) {
        UUID conversationId = UUID.randomUUID();
        jdbcTemplate.update(
            """
            INSERT INTO tb_conversation(id, tenant_id, channel_id, customer_id, status, trace_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            conversationId,
            tenantId,
            DEFAULT_CHANNEL_ID,
            DEFAULT_CUSTOMER_ID,
            TraceIdNormalizer.toUuid(traceId)
        );
        return findById(tenantId, conversationId).orElseThrow();
    }

    public Optional<ConversationView> findById(UUID tenantId, UUID conversationId) {
        List<ConversationView> list = jdbcTemplate.query(
            """
            SELECT id, tenant_id, channel_id, customer_id, status, trace_id, created_at
            FROM tb_conversation
            WHERE tenant_id = ?
              AND id = ?
            """,
            (rs, rowNum) -> new ConversationView(
                UUID.fromString(rs.getString("id")),
                UUID.fromString(rs.getString("tenant_id")),
                UUID.fromString(rs.getString("channel_id")),
                UUID.fromString(rs.getString("customer_id")),
                rs.getString("status"),
                rs.getString("trace_id"),
                toInstant(rs.getTimestamp("created_at"))
            ),
            tenantId,
            conversationId
        );
        return list.stream().findFirst();
    }

    public int estimateSessionTokenUsage(UUID tenantId, UUID conversationId) {
        Integer usage = jdbcTemplate.queryForObject(
            """
            SELECT COALESCE(SUM(LENGTH(COALESCE(message_text, ''))), 0)
            FROM tb_message
            WHERE tenant_id = ?
              AND conversation_id = ?
            """,
            Integer.class,
            tenantId,
            conversationId
        );
        int chars = usage == null ? 0 : usage;
        return Math.max(0, chars / 4);
    }

    private Instant toInstant(Timestamp timestamp) {
        return timestamp == null ? Instant.now() : timestamp.toInstant();
    }
}
