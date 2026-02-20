package com.aichatbot.session.domain.mapper;

import com.aichatbot.session.infrastructure.ConversationRow;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface ConversationMapper {

    int create(@Param("conversationId") UUID conversationId,
               @Param("tenantId") UUID tenantId,
               @Param("channelId") UUID channelId,
               @Param("customerId") UUID customerId,
               @Param("traceId") UUID traceId);

    ConversationRow findById(@Param("tenantId") UUID tenantId, @Param("conversationId") UUID conversationId);

    Integer estimateSessionTokenUsage(@Param("tenantId") UUID tenantId, @Param("conversationId") UUID conversationId);

    UUID findTenantIdByConversationId(@Param("conversationId") UUID conversationId);
}
