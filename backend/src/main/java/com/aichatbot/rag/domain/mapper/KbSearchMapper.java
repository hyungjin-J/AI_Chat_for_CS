package com.aichatbot.rag.domain.mapper;

import com.aichatbot.rag.infrastructure.ChunkSearchRow;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface KbSearchMapper {

    List<ChunkSearchRow> findApprovedChunksByTenant(@Param("tenantId") UUID tenantId);
}
