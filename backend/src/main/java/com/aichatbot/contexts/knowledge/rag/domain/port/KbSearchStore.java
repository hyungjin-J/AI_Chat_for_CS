package com.aichatbot.contexts.knowledge.rag.domain.port;

import com.aichatbot.contexts.knowledge.rag.domain.model.ChunkSearchRow;
import java.util.List;
import java.util.UUID;

public interface KbSearchStore {

    List<ChunkSearchRow> findApprovedChunksByTenant(UUID tenantId);
}
