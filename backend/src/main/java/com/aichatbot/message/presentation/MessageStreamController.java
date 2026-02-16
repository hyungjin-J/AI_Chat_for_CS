package com.aichatbot.message.presentation;

import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.tenant.TenantContext;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/v1")
public class MessageStreamController {

    private final ExecutorService executorService = Executors.newCachedThreadPool();

    @GetMapping(value = "/sessions/{session_id}/messages/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamMessage(
        @PathVariable("session_id") String sessionId,
        @RequestParam(value = "prompt", defaultValue = "안녕하세요") String prompt,
        @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId
    ) {
        SseEmitter emitter = new SseEmitter(30_000L);
        executorService.execute(() -> emitDemoEvents(emitter, sessionId, prompt, lastEventId));
        return emitter;
    }

    private void emitDemoEvents(SseEmitter emitter, String sessionId, String prompt, String lastEventId) {
        int eventId = parseLastEventId(lastEventId) + 1;
        try {
            // 왜 필요한가: token 이벤트는 프론트가 "답변이 시작됨"을 즉시 보여줄 수 있게 한다.
            send(emitter, eventId++, "token", Map.of(
                "session_id", sessionId,
                "text", "문의 내용을 확인하고 있습니다."
            ));
            Thread.sleep(250L);

            // 왜 필요한가: tool 이벤트를 분리하면 운영자가 외부 호출/내부 동작을 추적할 수 있다.
            send(emitter, eventId++, "tool", Map.of(
                "tool_name", "rag_retrieve",
                "status", "completed",
                "tenant_key", TenantContext.getTenantKey()
            ));
            Thread.sleep(250L);

            // 왜 필요한가: citation 이벤트는 무근거 답변을 막기 위한 핵심 근거 정보다.
            send(emitter, eventId++, "citation", Map.of(
                "source_id", "KB-001",
                "title", "고객센터 운영 가이드",
                "score", 0.96
            ));
            Thread.sleep(250L);

            send(emitter, eventId++, "token", Map.of(
                "text", "현재 정책 기준으로는 배송 지연 시 환불 규정 확인이 필요합니다."
            ));
            Thread.sleep(250L);

            send(emitter, eventId, "done", Map.of(
                "message_id", "msg-demo-001",
                "trace_id", TraceContext.getTraceId(),
                "prompt_preview", sanitizePrompt(prompt)
            ));
            emitter.complete();
        } catch (Exception exception) {
            try {
                send(emitter, eventId++, "safe_response", Map.of(
                    "message", "지금은 근거를 확정하기 어려워 확인이 필요합니다."
                ));
                send(emitter, eventId, "error", Map.of(
                    "error_code", "SYS-STREAM-001",
                    "message", "스트리밍 처리 중 오류가 발생했습니다.",
                    "trace_id", TraceContext.getTraceId()
                ));
            } catch (IOException ignored) {
                // 왜 필요한가: 이미 연결이 종료되었으면 추가 전송이 불가능하므로 조용히 종료한다.
            }
            emitter.completeWithError(exception);
        }
    }

    private String sanitizePrompt(String prompt) {
        // 왜 필요한가: 프롬프트 원문을 그대로 로그/이벤트에 남기면 PII 노출 위험이 커진다.
        if (prompt == null || prompt.isBlank()) {
            return "";
        }
        String normalized = prompt.replaceAll("\\s+", " ").trim();
        return normalized.length() > 40 ? normalized.substring(0, 40) + "..." : normalized;
    }

    private int parseLastEventId(String lastEventId) {
        if (lastEventId == null || lastEventId.isBlank()) {
            return 0;
        }
        try {
            return Integer.parseInt(lastEventId);
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private void send(SseEmitter emitter, int id, String eventName, Object payload) throws IOException {
        emitter.send(
            SseEmitter.event()
                .id(String.valueOf(id))
                .name(eventName)
                .data(payload)
        );
    }
}
