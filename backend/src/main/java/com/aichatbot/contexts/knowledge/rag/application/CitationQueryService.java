package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.domain.port.CitationStore;
import com.aichatbot.contexts.knowledge.rag.domain.readmodel.CitationView;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class CitationQueryService {

    private final CitationStore citationStore;

    public CitationQueryService(CitationStore citationStore) {
        this.citationStore = citationStore;
    }

    public List<CitationView> findByMessageId(UUID tenantId, UUID messageId, Integer cursorRankNo, int limit) {
        return citationStore.findByMessageId(tenantId, messageId, cursorRankNo, limit);
    }
}
