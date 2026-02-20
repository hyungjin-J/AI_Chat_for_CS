package com.aichatbot.message.infrastructure;

import com.aichatbot.message.application.StreamEventView;
import com.aichatbot.message.domain.mapper.StreamEventMapper;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class StreamEventRepository {

    private final StreamEventMapper streamEventMapper;

    public StreamEventRepository(StreamEventMapper streamEventMapper) {
        this.streamEventMapper = streamEventMapper;
    }

    public void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, int eventSeq, String eventType, String payloadJson) {
        streamEventMapper.save(
            UUID.randomUUID(),
            tenantId,
            messageId,
            messageCreatedAt,
            eventSeq,
            eventType,
            payloadJson
        );
    }

    public List<StreamEventView> findByMessageFromSeq(UUID tenantId, UUID messageId, int fromEventSeqExclusive) {
        return streamEventMapper.findByMessageFromSeq(tenantId, messageId, fromEventSeqExclusive);
    }
}
