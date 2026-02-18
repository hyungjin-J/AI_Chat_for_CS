package com.aichatbot.rag.infrastructure;

import com.aichatbot.rag.application.CitationView;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class CitationRepository {

    private final JdbcTemplate jdbcTemplate;

    public CitationRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, UUID chunkId, int rankNo, String excerptMasked) {
        jdbcTemplate.update(
            """
            INSERT INTO tb_rag_citation(
                id,
                tenant_id,
                message_id,
                message_created_at,
                chunk_id,
                rank_no,
                excerpt_masked,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            UUID.randomUUID(),
            tenantId,
            messageId,
            Timestamp.from(messageCreatedAt),
            chunkId,
            rankNo,
            excerptMasked
        );
    }

    public List<CitationView> findByMessageId(UUID tenantId, UUID messageId) {
        return jdbcTemplate.query(
            """
            SELECT id, tenant_id, message_id, chunk_id, rank_no, excerpt_masked, created_at
            FROM tb_rag_citation
            WHERE tenant_id = ?
              AND message_id = ?
            ORDER BY rank_no ASC
            """,
            (rs, rowNum) -> new CitationView(
                UUID.fromString(rs.getString("id")),
                UUID.fromString(rs.getString("tenant_id")),
                UUID.fromString(rs.getString("message_id")),
                rs.getString("chunk_id") == null ? null : UUID.fromString(rs.getString("chunk_id")),
                rs.getInt("rank_no"),
                rs.getString("excerpt_masked"),
                toInstant(rs.getTimestamp("created_at"))
            ),
            tenantId,
            messageId
        );
    }

    private Instant toInstant(Timestamp timestamp) {
        return timestamp == null ? Instant.now() : timestamp.toInstant();
    }
}
