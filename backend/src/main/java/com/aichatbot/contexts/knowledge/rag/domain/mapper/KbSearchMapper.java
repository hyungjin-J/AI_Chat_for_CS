package com.aichatbot.contexts.knowledge.rag.domain.mapper;

import com.aichatbot.contexts.knowledge.rag.infrastructure.ChunkSearchRow;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface KbSearchMapper {

    List<ChunkSearchRow> findApprovedChunksByTenant(@Param("tenantId") UUID tenantId);
}

