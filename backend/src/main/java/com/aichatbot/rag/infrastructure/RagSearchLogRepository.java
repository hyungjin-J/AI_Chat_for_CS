package com.aichatbot.rag.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import com.aichatbot.rag.domain.mapper.RagSearchLogMapper;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class RagSearchLogRepository {

    private final RagSearchLogMapper ragSearchLogMapper;

    public RagSearchLogRepository(RagSearchLogMapper ragSearchLogMapper) {
        this.ragSearchLogMapper = ragSearchLogMapper;
    }

    public void save(UUID tenantId, UUID conversationId, String queryTextMasked, int topK, String traceId, String retrievalMode) {
        ragSearchLogMapper.save(
            UUID.randomUUID().toString(),
            tenantId.toString(),
            conversationId == null ? null : conversationId.toString(),
            queryTextMasked,
            topK,
            TraceIdNormalizer.toUuid(traceId).toString()
        );
    }
}
