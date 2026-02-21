package com.aichatbot.message.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.message.infrastructure.StreamEventRepository;
import com.aichatbot.session.infrastructure.ConversationRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class SseStreamService {

    private final MessageRepository messageRepository;
    private final ConversationRepository conversationRepository;
    private final StreamEventRepository streamEventRepository;
    private final SseConcurrencyGuard sseConcurrencyGuard;
    private final MvpObservabilityMetrics mvpObservabilityMetrics;
    private final ObjectMapper objectMapper;
    private final AppProperties appProperties;

    public SseStreamService(
        MessageRepository messageRepository,
        ConversationRepository conversationRepository,
        StreamEventRepository streamEventRepository,
        SseConcurrencyGuard sseConcurrencyGuard,
        MvpObservabilityMetrics mvpObservabilityMetrics,
        ObjectMapper objectMapper,
        AppProperties appProperties
    ) {
        this.messageRepository = messageRepository;
        this.conversationRepository = conversationRepository;
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
        String requestTraceId = TraceGuard.requireTraceId();
        MessageView answerMessage = requireMessageInTenant(tenantId, messageId);
        requireSessionInTenant(tenantId, sessionId);

        if (!answerMessage.conversationId().equals(sessionId)) {
            throw new ApiException(
                HttpStatus.NOT_FOUND,
                "API-004-404",
                ErrorCatalog.messageOf("API-004-404"),
                List.of("session_message_not_found")
            );
        }

        String userKey = principal.tenantId() + ":" + principal.userId();
        sseConcurrencyGuard.acquire(userKey);

        AtomicBoolean released = new AtomicBoolean(false);
        Runnable releaseGuard = () -> {
            // Why: onCompletion/onTimeout/onError/finally can race, so release only once.
            if (released.compareAndSet(false, true)) {
                sseConcurrencyGuard.release(userKey);
            }
        };

        SseEmitter emitter = new SseEmitter(60_000L);
        emitter.onCompletion(releaseGuard);
        emitter.onTimeout(releaseGuard);
        emitter.onError(ex -> releaseGuard.run());

        try {
            long streamOpenedAtNanos = System.nanoTime();
            boolean firstTokenRecorded = false;
            if (fromEventSeqExclusive <= 0) {
                send(
                    emitter,
                    0,
                    "heartbeat",
                    objectMapper.createObjectNode()
                        .put("status", "alive")
                        .put("trace_id", requestTraceId)
                );
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
                        .put("trace_id", requestTraceId)
                );
            } catch (IOException ignored) {
            }
            emitter.completeWithError(exception);
        } finally {
            releaseGuard.run();
        }

        return emitter;
    }

    private Object parsePayload(String payloadJson) throws IOException {
        if (payloadJson == null || payloadJson.isBlank()) {
            return objectMapper.createObjectNode();
        }
        return objectMapper.readTree(payloadJson);
    }

    private MessageView requireMessageInTenant(UUID tenantId, UUID messageId) {
        MessageView message = messageRepository.findById(tenantId, messageId).orElse(null);
        if (message != null) {
            return message;
        }

        MessageView anyTenantMessage = messageRepository.findByIdWithoutTenant(messageId).orElse(null);
        // Why: Returning 403 for cross-tenant access prevents hiding authorization errors as not-found.
        if (anyTenantMessage != null && !anyTenantMessage.tenantId().equals(tenantId)) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                ErrorCatalog.messageOf("SEC-002-403"),
                List.of("cross_tenant_message_access")
            );
        }

        throw new ApiException(
            HttpStatus.NOT_FOUND,
            "API-004-404",
            ErrorCatalog.messageOf("API-004-404"),
            List.of("message_not_found")
        );
    }

    private void requireSessionInTenant(UUID tenantId, UUID sessionId) {
        if (conversationRepository.findById(tenantId, sessionId).isPresent()) {
            return;
        }

        // Why: Distinguishing 403 vs 404 keeps tenant isolation behavior deterministic for clients.
        UUID ownerTenantId = conversationRepository.findTenantIdByConversationId(sessionId).orElse(null);
        if (ownerTenantId != null && !ownerTenantId.equals(tenantId)) {
            throw new ApiException(
                HttpStatus.FORBIDDEN,
                "SEC-002-403",
                ErrorCatalog.messageOf("SEC-002-403"),
                List.of("cross_tenant_session_access")
            );
        }

        throw new ApiException(
            HttpStatus.NOT_FOUND,
            "API-004-404",
            ErrorCatalog.messageOf("API-004-404"),
            List.of("session_not_found")
        );
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
