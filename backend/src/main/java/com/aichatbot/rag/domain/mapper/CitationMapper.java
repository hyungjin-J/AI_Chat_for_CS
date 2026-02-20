package com.aichatbot.rag.domain.mapper;

import com.aichatbot.rag.infrastructure.CitationRow;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface CitationMapper {

    int save(@Param("citationId") UUID citationId,
             @Param("tenantId") UUID tenantId,
             @Param("messageId") UUID messageId,
             @Param("messageCreatedAt") Instant messageCreatedAt,
             @Param("chunkId") UUID chunkId,
             @Param("rankNo") int rankNo,
             @Param("excerptMasked") String excerptMasked);

    List<CitationRow> findByMessageId(@Param("tenantId") UUID tenantId,
                                      @Param("messageId") UUID messageId,
                                      @Param("cursorRankNo") Integer cursorRankNo,
                                      @Param("limit") int limit);
}
