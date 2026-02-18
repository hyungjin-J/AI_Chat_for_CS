package com.aichatbot.session.presentation;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.idempotency.IdempotencyService;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.message.application.MessageGenerationResult;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.presentation.dto.MessageAcceptedResponse;
import com.aichatbot.message.presentation.dto.MessageListResponse;
import com.aichatbot.session.application.ConversationView;
import com.aichatbot.session.application.SessionService;
import com.aichatbot.session.presentation.dto.CreateSessionRequest;
import com.aichatbot.session.presentation.dto.SessionResponse;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1")
public class SessionController {

    private final SessionService sessionService;
    private final IdempotencyService idempotencyService;

    public SessionController(SessionService sessionService, IdempotencyService idempotencyService) {
        this.sessionService = sessionService;
        this.idempotencyService = idempotencyService;
    }

    @GetMapping("/chat/bootstrap")
    public Map<String, Object> bootstrap() {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        return sessionService.bootstrap(
            TenantContext.getTenantKey(),
            UUID.fromString(TenantContext.getTenantId()),
            principal.userId(),
            principal.roles()
        );
    }

    @PostMapping("/sessions")
    public ResponseEntity<SessionResponse> createSession(
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody(required = false) CreateSessionRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        String key = requireIdempotencyKey(idempotencyKey);
        ConversationView created = idempotencyService.execute(
            "session:create:" + tenantId,
            key,
            () -> sessionService.createSession(tenantId)
        );

        SessionResponse response = new SessionResponse(
            "accepted",
            created.id().toString(),
            created.status(),
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/sessions/{session_id}")
    public ResponseEntity<SessionResponse> getSession(@PathVariable("session_id") String sessionId) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        ConversationView session = sessionService.getSession(tenantId, parseUuid(sessionId, "session_id"));
        SessionResponse response = new SessionResponse(
            "ok",
            session.id().toString(),
            session.status(),
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.ok(response);
    }

    @GetMapping("/sessions/{session_id}/messages")
    public ResponseEntity<MessageListResponse> listMessages(@PathVariable("session_id") String sessionId) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        List<MessageView> messages = sessionService.listMessages(tenantId, parseUuid(sessionId, "session_id"));
        List<MessageListResponse.MessageItem> items = messages.stream()
            .map(message -> new MessageListResponse.MessageItem(
                message.id().toString(),
                message.role(),
                message.messageText(),
                message.createdAt().toString(),
                message.traceId()
            ))
            .toList();
        return ResponseEntity.ok(new MessageListResponse(items, items.size(), TraceGuard.requireTraceId()));
    }

    @PostMapping("/sessions/{session_id}/messages")
    public ResponseEntity<MessageAcceptedResponse> postMessage(
        @PathVariable("session_id") String sessionId,
        @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
        @Valid @RequestBody com.aichatbot.message.presentation.dto.PostMessageRequest request
    ) {
        UUID tenantId = UUID.fromString(TenantContext.getTenantId());
        UUID conversationId = parseUuid(sessionId, "session_id");
        String key = requireIdempotencyKey(idempotencyKey);

        MessageGenerationResult result = idempotencyService.execute(
            "message:post:" + tenantId + ":" + conversationId,
            key,
            () -> sessionService.generateAnswer(tenantId, conversationId, request.text(), request.topK())
        );

        MessageAcceptedResponse response = new MessageAcceptedResponse(
            "accepted",
            result.answerMessageId(),
            conversationId.toString(),
            TraceGuard.requireTraceId()
        );
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(response);
    }

    private UUID parseUuid(String raw, String field) {
        try {
            return UUID.fromString(raw);
        } catch (IllegalArgumentException exception) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of(field + "_invalid")
            );
        }
    }

    private String requireIdempotencyKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "API-003-422",
                ErrorCatalog.messageOf("API-003-422"),
                List.of("idempotency_key_required")
            );
        }
        return idempotencyKey.trim();
    }
}
