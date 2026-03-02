package com.aichatbot.contexts.knowledge.rag.application;

import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class NoopKbSearchIndexer implements KbSearchIndexer {

    @Override
    public void verifyWritable(UUID tenantId, UUID documentVersionId) {
        if (tenantId == null || documentVersionId == null) {
            throw new KbIndexingStageException("KB-INDEX-SEARCH-422", "search index verification input was invalid", false);
        }
    }
}
