package com.aichatbot.rag.infrastructure;

import com.aichatbot.global.observability.TraceGuard;
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
        // Why: Query logs are audit evidence for retrieval, so they must share the ingress trace_id.
        UUID requiredTraceId = UUID.fromString(TraceGuard.requireTraceId());
        ragSearchLogMapper.save(
            UUID.randomUUID(),
            tenantId,
            conversationId,
            queryTextMasked,
            topK,
            requiredTraceId
        );
    }

    public String findLatestMaskedQueryByConversation(UUID tenantId, UUID conversationId) {
        return ragSearchLogMapper.findLatestMaskedQueryByConversation(tenantId, conversationId);
    }

    public String findLatestTraceIdByConversation(UUID tenantId, UUID conversationId) {
        return ragSearchLogMapper.findLatestTraceIdByConversation(tenantId, conversationId);
    }
}
