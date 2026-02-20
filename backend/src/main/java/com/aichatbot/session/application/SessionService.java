package com.aichatbot.session.application;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.message.application.MessageGenerationResult;
import com.aichatbot.message.application.MessageGenerationService;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.session.infrastructure.ConversationRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class SessionService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final MessageGenerationService messageGenerationService;

    public SessionService(
        ConversationRepository conversationRepository,
        MessageRepository messageRepository,
        MessageGenerationService messageGenerationService
    ) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.messageGenerationService = messageGenerationService;
    }

    public Map<String, Object> bootstrap(String tenantKey, UUID tenantId, String userId, List<String> roles) {
        return Map.of(
            "result", "ok",
            "data", Map.of(
                "tenant_key", tenantKey,
                "tenant_id", tenantId.toString(),
                "user_id", userId,
                "roles", roles,
                "answer_contract_version", "v1",
                "sse_event_types", List.of("token", "tool", "citation", "heartbeat", "error", "safe_response", "done")
            ),
            "trace_id", TraceGuard.requireTraceId()
        );
    }

    public ConversationView createSession(UUID tenantId) {
        return conversationRepository.create(tenantId, TraceGuard.requireTraceId());
    }

    public ConversationView getSession(UUID tenantId, UUID sessionId) {
        return requireSessionInTenant(tenantId, sessionId);
    }

    public List<MessageView> listMessages(UUID tenantId, UUID sessionId) {
        requireSessionInTenant(tenantId, sessionId);
        return messageRepository.findByConversation(tenantId, sessionId);
    }

    public MessageGenerationResult generateAnswer(UUID tenantId, UUID sessionId, String text, Integer topK) {
        requireSessionInTenant(tenantId, sessionId);
        return messageGenerationService.generate(tenantId, sessionId, text, topK);
    }

    private ConversationView requireSessionInTenant(UUID tenantId, UUID sessionId) {
        ConversationView conversation = conversationRepository.findById(tenantId, sessionId).orElse(null);
        if (conversation != null) {
            return conversation;
        }

        // Why: "없는 세션"과 "타 테넌트 세션"을 분리해야 운영 시 원인(데이터 없음 vs 권한 문제)을 바로 알 수 있습니다.
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
}
