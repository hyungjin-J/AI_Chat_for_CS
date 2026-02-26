package com.aichatbot.contexts.knowledge.rag.infrastructure;

import com.aichatbot.contexts.knowledge.rag.domain.mapper.KbSearchMapper;
import com.aichatbot.contexts.knowledge.rag.domain.model.ChunkSearchRow;
import com.aichatbot.contexts.knowledge.rag.domain.port.KbSearchStore;
import java.util.List;
import java.util.UUID;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Repository;

@Primary
@Repository
public class KbSearchRepository implements KbSearchStore {

    private final KbSearchMapper kbSearchMapper;

    public KbSearchRepository(KbSearchMapper kbSearchMapper) {
        this.kbSearchMapper = kbSearchMapper;
    }

    @Override
    public List<ChunkSearchRow> findApprovedChunksByTenant(UUID tenantId) {
        return kbSearchMapper.findApprovedChunksByTenant(tenantId);
    }
}

