package com.aichatbot.message.infrastructure;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.message.application.StreamEventView;
import com.aichatbot.message.domain.mapper.StreamEventMapper;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Repository;

@Repository
public class StreamEventRepository {

    private final StreamEventMapper streamEventMapper;

    public StreamEventRepository(StreamEventMapper streamEventMapper) {
        this.streamEventMapper = streamEventMapper;
    }

    public void save(UUID tenantId, UUID messageId, Instant messageCreatedAt, int eventSeq, String eventType, String payloadJson) {
        // Why: Stream event rows are part of audit trail; missing trace_id in payload is a policy violation.
        TraceGuard.requireTraceId();
        if (payloadJson == null || !payloadJson.contains("\"trace_id\"")) {
            throw new ApiException(
                HttpStatus.CONFLICT,
                "SYS-004-409-TRACE",
                ErrorCatalog.messageOf("SYS-004-409-TRACE"),
                List.of("stream_event_trace_id_missing")
            );
        }
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
