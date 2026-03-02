package com.aichatbot.contexts.knowledge.rag.application;

import java.util.UUID;

public interface KbSearchIndexer {

    void verifyWritable(UUID tenantId, UUID documentVersionId);
}
