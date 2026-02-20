package com.aichatbot.message.domain.mapper;

import com.aichatbot.message.infrastructure.MessageRow;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface MessageMapper {

    int create(@Param("messageId") UUID messageId,
               @Param("tenantId") UUID tenantId,
               @Param("conversationId") UUID conversationId,
               @Param("role") String role,
               @Param("messageText") String messageText,
               @Param("traceId") UUID traceId);

    MessageRow findById(@Param("tenantId") UUID tenantId, @Param("messageId") UUID messageId);

    List<MessageRow> findByConversation(@Param("tenantId") UUID tenantId,
                                        @Param("conversationId") UUID conversationId);
}
