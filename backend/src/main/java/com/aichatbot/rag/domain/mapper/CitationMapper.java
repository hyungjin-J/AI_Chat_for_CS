package com.aichatbot.rag.domain.mapper;

import com.aichatbot.rag.infrastructure.CitationRow;
import java.time.Instant;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface CitationMapper {

    int save(@Param("citationId") String citationId,
             @Param("tenantId") String tenantId,
             @Param("messageId") String messageId,
             @Param("messageCreatedAt") Instant messageCreatedAt,
             @Param("chunkId") String chunkId,
             @Param("rankNo") int rankNo,
             @Param("excerptMasked") String excerptMasked);

    List<CitationRow> findByMessageId(@Param("tenantId") String tenantId,
                                      @Param("messageId") String messageId,
                                      @Param("cursorRankNo") Integer cursorRankNo,
                                      @Param("limit") int limit);
}
