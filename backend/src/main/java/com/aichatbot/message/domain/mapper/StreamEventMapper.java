package com.aichatbot.message.domain.mapper;

import com.aichatbot.message.application.StreamEventView;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.apache.ibatis.annotations.Param;

public interface StreamEventMapper {

    int save(@Param("streamEventId") UUID streamEventId,
             @Param("tenantId") UUID tenantId,
             @Param("messageId") UUID messageId,
             @Param("messageCreatedAt") Instant messageCreatedAt,
             @Param("eventSeq") int eventSeq,
             @Param("eventType") String eventType,
             @Param("payloadJson") String payloadJson);

    List<StreamEventView> findByMessageFromSeq(@Param("tenantId") UUID tenantId,
                                               @Param("messageId") UUID messageId,
                                               @Param("fromEventSeqExclusive") int fromEventSeqExclusive);
}
