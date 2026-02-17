package com.aichatbot.message.presentation;

import com.aichatbot.billing.application.BudgetEnforcementService;
import com.aichatbot.billing.application.GenerationLogService;
import com.aichatbot.global.observability.TraceContext;
import com.aichatbot.global.tenant.TenantContext;
import java.io.IOException;
import java.util.Map;
import java.util.UUID;
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

    private static final String DEFAULT_PROVIDER = "provider-default";
    private static final String DEFAULT_MODEL = "model-default";

    private final BudgetEnforcementService budgetEnforcementService;
    private final GenerationLogService generationLogService;
    private final ExecutorService executorService = Executors.newCachedThreadPool();

    public MessageStreamController(
        BudgetEnforcementService budgetEnforcementService,
        GenerationLogService generationLogService
    ) {
        this.budgetEnforcementService = budgetEnforcementService;
        this.generationLogService = generationLogService;
    }

    @GetMapping(value = "/sessions/{session_id}/messages/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamMessage(
        @PathVariable("session_id") String sessionId,
        @RequestParam(value = "prompt", defaultValue = "안녕하세요") String prompt,
        @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId
    ) {
        int inputTokens = estimateTokenCount(prompt);
        int outputTokens = 256;
        int toolCalls = 1;
        String tenantId = requireTenantId();

        budgetEnforcementService.enforceGenerationBudget(
            tenantId,
            DEFAULT_PROVIDER,
            DEFAULT_MODEL,
            inputTokens,
            outputTokens,
            toolCalls
        );

        String messageId = "msg-" + UUID.randomUUID();
        generationLogService.record(
            messageId,
            DEFAULT_PROVIDER,
            DEFAULT_MODEL,
            inputTokens,
            outputTokens,
            toolCalls,
            prompt
        );

        SseEmitter emitter = new SseEmitter(30_000L);
        executorService.execute(() -> emitDemoEvents(emitter, sessionId, messageId, prompt, lastEventId));
        return emitter;
    }

    private void emitDemoEvents(SseEmitter emitter, String sessionId, String messageId, String prompt, String lastEventId) {
        int eventId = parseLastEventId(lastEventId) + 1;
        try {
            send(emitter, eventId++, "token", Map.of(
                "session_id", sessionId,
                "text", "문의 내용을 확인하고 있습니다."
            ));
            Thread.sleep(250L);

            send(emitter, eventId++, "tool", Map.of(
                "tool_name", "rag_retrieve",
                "status", "completed",
                "tenant_key", TenantContext.getTenantKey()
            ));
            Thread.sleep(250L);

            send(emitter, eventId++, "citation", Map.of(
                "source_id", "KB-001",
                "title", "고객센터 운영 가이드",
                "score", 0.96
            ));
            Thread.sleep(250L);

            send(emitter, eventId++, "token", Map.of(
                "text", "현재 정책 기준으로는 배송 지연 보상 규정 확인이 필요합니다."
            ));
            Thread.sleep(250L);

            send(emitter, eventId, "done", Map.of(
                "message_id", messageId,
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
                // Why: 클라이언트 연결이 종료된 경우 추가 이벤트 전송 시도는 의미가 없으므로 무시한다.
            }
            emitter.completeWithError(exception);
        }
    }

    private String requireTenantId() {
        String tenantId = TenantContext.getTenantKey();
        if (tenantId == null || tenantId.isBlank()) {
            throw new IllegalStateException("X-Tenant-Key is required");
        }
        return tenantId;
    }

    private int estimateTokenCount(String prompt) {
        if (prompt == null || prompt.isBlank()) {
            return 1;
        }
        int normalizedLength = prompt.trim().length();
        return Math.max(1, normalizedLength / 4);
    }

    private String sanitizePrompt(String prompt) {
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

