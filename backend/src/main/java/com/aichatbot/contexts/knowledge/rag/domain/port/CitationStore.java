package com.aichatbot.contexts.knowledge.rag.domain.port;

import com.aichatbot.contexts.knowledge.rag.domain.readmodel.CitationView;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public interface CitationStore {

    void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, UUID chunkId, int rankNo, String excerptMasked);

    List<CitationView> findByMessageId(UUID tenantId, UUID messageId, Integer cursorRankNo, int limit);
}
