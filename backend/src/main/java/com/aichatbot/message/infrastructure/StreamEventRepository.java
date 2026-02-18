package com.aichatbot.message.infrastructure;

import com.aichatbot.message.application.StreamEventView;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class StreamEventRepository {

    private final JdbcTemplate jdbcTemplate;

    public StreamEventRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, int eventSeq, String eventType, String payloadJson) {
        jdbcTemplate.update(
            """
            INSERT INTO tb_stream_event(
                id,
                tenant_id,
                message_id,
                message_created_at,
                event_type,
                event_seq,
                payload_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CAST(? AS JSON), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            UUID.randomUUID(),
            tenantId,
            messageId,
            Timestamp.from(messageCreatedAt),
            eventType,
            eventSeq,
            payloadJson
        );
    }

    public List<StreamEventView> findByMessageFromSeq(UUID tenantId, UUID messageId, int fromEventSeqExclusive) {
        return jdbcTemplate.query(
            """
            SELECT event_seq, event_type, CAST(payload_json AS VARCHAR) AS payload_json
            FROM tb_stream_event
            WHERE tenant_id = ?
              AND message_id = ?
              AND event_seq > ?
            ORDER BY event_seq ASC
            """,
            (rs, rowNum) -> new StreamEventView(
                rs.getInt("event_seq"),
                rs.getString("event_type"),
                rs.getString("payload_json")
            ),
            tenantId,
            messageId,
            fromEventSeqExclusive
        );
    }
}
