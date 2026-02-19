package com.aichatbot.rag.domain.mapper;

import org.apache.ibatis.annotations.Param;

public interface RagSearchLogMapper {

    int save(@Param("ragSearchLogId") String ragSearchLogId,
             @Param("tenantId") String tenantId,
             @Param("conversationId") String conversationId,
             @Param("queryTextMasked") String queryTextMasked,
             @Param("topK") int topK,
             @Param("traceId") String traceId);
}
