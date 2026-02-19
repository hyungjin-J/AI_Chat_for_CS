package com.aichatbot.message.domain.mapper;

import com.aichatbot.message.infrastructure.MessageRow;
import java.util.List;
import org.apache.ibatis.annotations.Param;

public interface MessageMapper {

    int create(@Param("messageId") String messageId,
               @Param("tenantId") String tenantId,
               @Param("conversationId") String conversationId,
               @Param("role") String role,
               @Param("messageText") String messageText,
               @Param("traceId") String traceId);

    MessageRow findById(@Param("tenantId") String tenantId, @Param("messageId") String messageId);

    List<MessageRow> findByConversation(@Param("tenantId") String tenantId,
                                        @Param("conversationId") String conversationId);
}
