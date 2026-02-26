package com.aichatbot.contexts.knowledge.rag.infrastructure;

import com.aichatbot.platform.observability.TraceGuard;
import com.aichatbot.contexts.knowledge.rag.domain.mapper.RagSearchLogMapper;
import com.aichatbot.contexts.knowledge.rag.domain.port.RagSearchLogStore;
import java.util.UUID;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Repository;

@Primary
@Repository
public class RagSearchLogRepository implements RagSearchLogStore {

    private final RagSearchLogMapper ragSearchLogMapper;

    public RagSearchLogRepository(RagSearchLogMapper ragSearchLogMapper) {
        this.ragSearchLogMapper = ragSearchLogMapper;
    }

    @Override
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

    @Override
    public String findLatestMaskedQueryByConversation(UUID tenantId, UUID conversationId) {
        return ragSearchLogMapper.findLatestMaskedQueryByConversation(tenantId, conversationId);
    }

    @Override
    public String findLatestTraceIdByConversation(UUID tenantId, UUID conversationId) {
        return ragSearchLogMapper.findLatestTraceIdByConversation(tenantId, conversationId);
    }
}

