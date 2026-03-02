package com.aichatbot.contexts.conversation.session.application;

import com.aichatbot.contexts.conversation.session.presentation.dto.CoreSessionActionResponse;
import com.aichatbot.contexts.conversation.session.presentation.dto.CsatPostRequest;
import com.aichatbot.contexts.conversation.session.presentation.dto.HandoffRequest;
import com.aichatbot.contexts.conversation.session.presentation.dto.MessageRetryRequest;
import com.aichatbot.contexts.conversation.session.presentation.dto.QuickReplyPostRequest;
import com.aichatbot.contexts.conversation.session.presentation.dto.SessionCloseRequest;
import com.aichatbot.platform.observability.TraceGuard;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class CoreSessionActionService {

    private final SessionService sessionService;

    public CoreSessionActionService(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    public CoreSessionActionResponse closeSession(UUID tenantId, UUID sessionId, SessionCloseRequest request) {
        sessionService.getSession(tenantId, sessionId);
        return response("session_close", sessionId);
    }

    public CoreSessionActionResponse retryMessage(
        UUID tenantId,
        UUID sessionId,
        UUID messageId,
        MessageRetryRequest request
    ) {
        sessionService.getSession(tenantId, sessionId);
        return response("message_retry", sessionId);
    }

    public CoreSessionActionResponse postQuickReply(
        UUID tenantId,
        UUID sessionId,
        UUID quickReplyId,
        QuickReplyPostRequest request
    ) {
        sessionService.getSession(tenantId, sessionId);
        return response("quick_reply", sessionId);
    }

    public CoreSessionActionResponse postCsat(UUID tenantId, UUID sessionId, CsatPostRequest request) {
        sessionService.getSession(tenantId, sessionId);
        return response("csat_submit", sessionId);
    }

    public CoreSessionActionResponse requestHandoff(UUID tenantId, UUID sessionId, HandoffRequest request) {
        sessionService.getSession(tenantId, sessionId);
        return response("handoff_request", sessionId);
    }

    private CoreSessionActionResponse response(String action, UUID sessionId) {
        return new CoreSessionActionResponse("accepted", action, sessionId.toString(), TraceGuard.requireTraceId());
    }
}
