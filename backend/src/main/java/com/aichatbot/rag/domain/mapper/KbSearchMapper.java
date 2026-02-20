package com.aichatbot.rag.domain.mapper;

import com.aichatbot.rag.infrastructure.ChunkSearchRow;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface KbSearchMapper {

    List<ChunkSearchRow> findApprovedChunksByTenant(@Param("tenantId") String tenantId);
}
