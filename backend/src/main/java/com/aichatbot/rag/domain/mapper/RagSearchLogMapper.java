package com.aichatbot.rag.domain.mapper;

import org.apache.ibatis.annotations.Param;
import java.util.UUID;

public interface RagSearchLogMapper {

    int save(@Param("ragSearchLogId") UUID ragSearchLogId,
             @Param("tenantId") UUID tenantId,
             @Param("conversationId") UUID conversationId,
             @Param("queryTextMasked") String queryTextMasked,
             @Param("topK") int topK,
             @Param("traceId") UUID traceId);

    String findLatestMaskedQueryByConversation(@Param("tenantId") UUID tenantId,
                                               @Param("conversationId") UUID conversationId);
}
