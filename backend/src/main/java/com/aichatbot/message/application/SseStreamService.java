package com.aichatbot.message.application;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.message.infrastructure.StreamEventRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class SseStreamService {

    private final MessageRepository messageRepository;
    private final StreamEventRepository streamEventRepository;
    private final SseConcurrencyGuard sseConcurrencyGuard;
    private final MvpObservabilityMetrics mvpObservabilityMetrics;
    private final ObjectMapper objectMapper;
    private final AppProperties appProperties;

    public SseStreamService(
        MessageRepository messageRepository,
        StreamEventRepository streamEventRepository,
        SseConcurrencyGuard sseConcurrencyGuard,
        MvpObservabilityMetrics mvpObservabilityMetrics,
        ObjectMapper objectMapper,
        AppProperties appProperties
    ) {
        this.messageRepository = messageRepository;
        this.streamEventRepository = streamEventRepository;
        this.sseConcurrencyGuard = sseConcurrencyGuard;
        this.mvpObservabilityMetrics = mvpObservabilityMetrics;
        this.objectMapper = objectMapper;
        this.appProperties = appProperties;
    }

    public SseEmitter stream(
        UUID tenantId,
        UUID sessionId,
        UUID messageId,
        int fromEventSeqExclusive,
        UserPrincipal principal
    ) {
        MessageView answerMessage = messageRepository.findById(tenantId, messageId)
            .orElseThrow(() -> new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("message_not_found")
            ));

        if (!answerMessage.conversationId().equals(sessionId)) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("session_message_mismatch")
            );
        }

        String userKey = principal.tenantId() + ":" + principal.userId();
        sseConcurrencyGuard.acquire(userKey);

        SseEmitter emitter = new SseEmitter(60_000L);
        emitter.onCompletion(() -> sseConcurrencyGuard.release(userKey));
        emitter.onTimeout(() -> sseConcurrencyGuard.release(userKey));
        emitter.onError(ex -> sseConcurrencyGuard.release(userKey));

        try {
            long streamOpenedAtNanos = System.nanoTime();
            boolean firstTokenRecorded = false;
            if (fromEventSeqExclusive <= 0) {
                send(emitter, 0, "heartbeat", objectMapper.createObjectNode().put("status", "alive"));
            }
            List<StreamEventView> events = streamEventRepository.findByMessageFromSeq(tenantId, messageId, fromEventSeqExclusive);
            for (StreamEventView event : events) {
                Object payload = parsePayload(event.payloadJson());
                send(emitter, event.eventSeq(), event.eventType(), payload);
                if (!firstTokenRecorded && "token".equals(event.eventType())) {
                    long elapsedMs = (System.nanoTime() - streamOpenedAtNanos) / 1_000_000L;
                    mvpObservabilityMetrics.recordSseFirstToken(elapsedMs);
                    firstTokenRecorded = true;
                }
            }
            long holdMs = Math.max(0L, appProperties.getBudget().getSseHoldMs());
            if (holdMs > 0L) {
                Thread.sleep(holdMs);
            }
            emitter.complete();
        } catch (InterruptedException interruptedException) {
            Thread.currentThread().interrupt();
            emitter.completeWithError(interruptedException);
        } catch (Exception exception) {
            try {
                send(
                    emitter,
                    fromEventSeqExclusive + 999,
                    "error",
                    objectMapper.createObjectNode()
                        .put("error_code", "SYS-003-500")
                        .put("message", ErrorCatalog.messageOf("SYS-003-500"))
                );
            } catch (IOException ignored) {
            }
            emitter.completeWithError(exception);
        }

        return emitter;
    }

    private Object parsePayload(String payloadJson) throws IOException {
        if (payloadJson == null || payloadJson.isBlank()) {
            return objectMapper.createObjectNode();
        }
        return objectMapper.readTree(payloadJson);
    }

    private void send(SseEmitter emitter, int eventSeq, String eventName, Object payload) throws IOException {
        emitter.send(
            SseEmitter.event()
                .id(String.valueOf(eventSeq))
                .name(eventName)
                .data(payload)
        );
    }
}
