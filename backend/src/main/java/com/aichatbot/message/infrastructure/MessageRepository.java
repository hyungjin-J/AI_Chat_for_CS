package com.aichatbot.message.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import com.aichatbot.message.application.MessageView;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class MessageRepository {

    private final JdbcTemplate jdbcTemplate;

    public MessageRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public MessageView create(UUID tenantId, UUID conversationId, String role, String messageText, String traceId) {
        UUID messageId = UUID.randomUUID();
        jdbcTemplate.update(
            """
            INSERT INTO tb_message(
                id,
                tenant_id,
                conversation_id,
                role,
                message_text,
                trace_id,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            messageId,
            tenantId,
            conversationId,
            role,
            messageText,
            TraceIdNormalizer.toUuid(traceId)
        );
        return findById(tenantId, messageId).orElseThrow();
    }

    public Optional<MessageView> findById(UUID tenantId, UUID messageId) {
        List<MessageView> messages = jdbcTemplate.query(
            """
            SELECT id, tenant_id, conversation_id, role, message_text, trace_id, created_at
            FROM tb_message
            WHERE tenant_id = ?
              AND id = ?
            """,
            (rs, rowNum) -> new MessageView(
                UUID.fromString(rs.getString("id")),
                UUID.fromString(rs.getString("tenant_id")),
                UUID.fromString(rs.getString("conversation_id")),
                rs.getString("role"),
                rs.getString("message_text"),
                rs.getString("trace_id"),
                toInstant(rs.getTimestamp("created_at"))
            ),
            tenantId,
            messageId
        );
        return messages.stream().findFirst();
    }

    public List<MessageView> findByConversation(UUID tenantId, UUID conversationId) {
        return jdbcTemplate.query(
            """
            SELECT id, tenant_id, conversation_id, role, message_text, trace_id, created_at
            FROM tb_message
            WHERE tenant_id = ?
              AND conversation_id = ?
            ORDER BY created_at ASC
            """,
            (rs, rowNum) -> new MessageView(
                UUID.fromString(rs.getString("id")),
                UUID.fromString(rs.getString("tenant_id")),
                UUID.fromString(rs.getString("conversation_id")),
                rs.getString("role"),
                rs.getString("message_text"),
                rs.getString("trace_id"),
                toInstant(rs.getTimestamp("created_at"))
            ),
            tenantId,
            conversationId
        );
    }

    private Instant toInstant(Timestamp timestamp) {
        return timestamp == null ? Instant.now() : timestamp.toInstant();
    }
}
