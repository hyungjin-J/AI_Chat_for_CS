package com.aichatbot.session.infrastructure;

import com.aichatbot.global.observability.TraceIdNormalizer;
import com.aichatbot.session.domain.mapper.ConversationMapper;
import com.aichatbot.session.application.ConversationView;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class ConversationRepository {

    private static final UUID DEFAULT_CHANNEL_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID DEFAULT_CUSTOMER_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");

    private final ConversationMapper conversationMapper;

    public ConversationRepository(ConversationMapper conversationMapper) {
        this.conversationMapper = conversationMapper;
    }

    public ConversationView create(UUID tenantId, String traceId) {
        UUID conversationId = UUID.randomUUID();
        conversationMapper.create(
            conversationId.toString(),
            tenantId.toString(),
            DEFAULT_CHANNEL_ID.toString(),
            DEFAULT_CUSTOMER_ID.toString(),
            TraceIdNormalizer.toUuid(traceId).toString()
        );
        return findById(tenantId, conversationId).orElseThrow();
    }

    public Optional<ConversationView> findById(UUID tenantId, UUID conversationId) {
        ConversationRow row = conversationMapper.findById(tenantId.toString(), conversationId.toString());
        if (row == null) {
            return Optional.empty();
        }
        return Optional.of(new ConversationView(
            UUID.fromString(row.id()),
            UUID.fromString(row.tenantId()),
            UUID.fromString(row.channelId()),
            UUID.fromString(row.customerId()),
            row.status(),
            row.traceId(),
            row.createdAt()
        ));
    }

    public int estimateSessionTokenUsage(UUID tenantId, UUID conversationId) {
        Integer usage = conversationMapper.estimateSessionTokenUsage(tenantId.toString(), conversationId.toString());
        int chars = usage == null ? 0 : usage;
        return Math.max(0, chars / 4);
    }
}
