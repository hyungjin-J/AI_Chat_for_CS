package com.aichatbot.message.presentation;

import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.global.security.UserPrincipal;
import com.aichatbot.global.tenant.TenantContext;
import com.aichatbot.message.application.SseStreamService;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/v1/sessions/{session_id}/messages/{message_id}")
public class MessageStreamV1Controller {

    private final SseStreamService sseStreamService;

    public MessageStreamV1Controller(SseStreamService sseStreamService) {
        this.sseStreamService = sseStreamService;
    }

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(
        @PathVariable("session_id") String sessionId,
        @PathVariable("message_id") String messageId,
        @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
        @RequestParam(value = "last_event_id", required = false) String lastEventIdQuery
    ) {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        int fromSeq = parseEventSeq(lastEventIdQuery != null ? lastEventIdQuery : lastEventId);
        return sseStreamService.stream(
            UUID.fromString(TenantContext.getTenantId()),
            parseUuid(sessionId, "session_id"),
            parseUuid(messageId, "message_id"),
            fromSeq,
            principal
        );
    }

    @GetMapping(value = "/stream/resume", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter resume(
        @PathVariable("session_id") String sessionId,
        @PathVariable("message_id") String messageId,
        @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
        @RequestParam(value = "last_event_id", required = false) String lastEventIdQuery
    ) {
        UserPrincipal principal = PrincipalUtils.currentPrincipal();
        int fromSeq = parseEventSeq(lastEventIdQuery != null ? lastEventIdQuery : lastEventId);
        return sseStreamService.stream(
            UUID.fromString(TenantContext.getTenantId()),
            parseUuid(sessionId, "session_id"),
            parseUuid(messageId, "message_id"),
            fromSeq,
            principal
        );
    }

    private int parseEventSeq(String raw) {
        if (raw == null || raw.isBlank()) {
            return 0;
        }
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException exception) {
            return 0;
        }
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
}
