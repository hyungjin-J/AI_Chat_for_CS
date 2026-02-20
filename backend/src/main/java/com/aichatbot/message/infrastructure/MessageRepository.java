package com.aichatbot.message.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.domain.mapper.MessageMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class MessageRepository {

    private final MessageMapper messageMapper;

    public MessageRepository(MessageMapper messageMapper) {
        this.messageMapper = messageMapper;
    }

    public MessageView create(UUID tenantId, UUID conversationId, String role, String messageText, String traceId) {
        UUID messageId = UUID.randomUUID();
        messageMapper.create(
            messageId,
            tenantId,
            conversationId,
            role,
            messageText,
            TraceIdNormalizer.toUuid(traceId)
        );
        return findById(tenantId, messageId).orElseThrow();
    }

    public Optional<MessageView> findById(UUID tenantId, UUID messageId) {
        MessageRow row = messageMapper.findById(tenantId, messageId);
        if (row == null) {
            return Optional.empty();
        }
        return Optional.of(toMessageView(row));
    }

    public Optional<MessageView> findByIdWithoutTenant(UUID messageId) {
        MessageRow row = messageMapper.findByIdWithoutTenant(messageId);
        if (row == null) {
            return Optional.empty();
        }
        return Optional.of(toMessageView(row));
    }

    public List<MessageView> findByConversation(UUID tenantId, UUID conversationId) {
        List<MessageRow> rows = messageMapper.findByConversation(tenantId, conversationId);
        List<MessageView> views = new ArrayList<>(rows.size());
        for (MessageRow row : rows) {
            views.add(toMessageView(row));
        }
        return views;
    }

    private MessageView toMessageView(MessageRow row) {
        return new MessageView(
            UUID.fromString(row.id()),
            UUID.fromString(row.tenantId()),
            UUID.fromString(row.conversationId()),
            row.role(),
            row.messageText(),
            row.traceId(),
            row.createdAt()
        );
    }
}
