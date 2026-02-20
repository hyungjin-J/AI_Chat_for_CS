package com.aichatbot.rag.infrastructure;

import com.aichatbot.rag.domain.mapper.KbSearchMapper;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class KbSearchRepository {

    private final KbSearchMapper kbSearchMapper;

    public KbSearchRepository(KbSearchMapper kbSearchMapper) {
        this.kbSearchMapper = kbSearchMapper;
    }

    public List<ChunkSearchRow> findApprovedChunksByTenant(UUID tenantId) {
        return kbSearchMapper.findApprovedChunksByTenant(tenantId.toString());
    }
}
