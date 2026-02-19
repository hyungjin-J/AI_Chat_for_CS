package com.aichatbot.session.domain.mapper;

import com.aichatbot.session.infrastructure.ConversationRow;
import org.apache.ibatis.annotations.Param;

public interface ConversationMapper {

    int create(@Param("conversationId") String conversationId,
               @Param("tenantId") String tenantId,
               @Param("channelId") String channelId,
               @Param("customerId") String customerId,
               @Param("traceId") String traceId);

    ConversationRow findById(@Param("tenantId") String tenantId, @Param("conversationId") String conversationId);

    Integer estimateSessionTokenUsage(@Param("tenantId") String tenantId, @Param("conversationId") String conversationId);
}
