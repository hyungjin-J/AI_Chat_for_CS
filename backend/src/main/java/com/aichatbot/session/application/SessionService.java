package com.aichatbot.session.application;

import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.message.application.MessageGenerationResult;
import com.aichatbot.message.application.MessageGenerationService;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.session.infrastructure.ConversationRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
        return conversationRepository.findById(tenantId, sessionId)
            .orElseThrow(() -> new IllegalArgumentException("session_not_found"));
    }

    public List<MessageView> listMessages(UUID tenantId, UUID sessionId) {
        return messageRepository.findByConversation(tenantId, sessionId);
    }

    public MessageGenerationResult generateAnswer(UUID tenantId, UUID sessionId, String text, Integer topK) {
        return messageGenerationService.generate(tenantId, sessionId, text, topK);
    }
}
