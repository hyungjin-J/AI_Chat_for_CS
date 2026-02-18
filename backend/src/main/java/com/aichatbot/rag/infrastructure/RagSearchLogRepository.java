package com.aichatbot.rag.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class RagSearchLogRepository {

    private final JdbcTemplate jdbcTemplate;

    public RagSearchLogRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void save(UUID tenantId, UUID conversationId, String queryTextMasked, int topK, String traceId, String retrievalMode) {
        String payload = "[mode=" + retrievalMode + "] " + queryTextMasked;
        jdbcTemplate.update(
            """
            INSERT INTO tb_rag_search_log(
                id,
                tenant_id,
                conversation_id,
                query_text_masked,
                top_k,
                trace_id,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            UUID.randomUUID(),
            tenantId,
            conversationId,
            payload,
            topK,
            TraceIdNormalizer.toUuid(traceId)
        );
    }
}
