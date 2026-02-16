#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 스캐폴딩 파일을 UTF-8로 생성/갱신하는 유틸리티.
CMD 배치에서 호출해도 인코딩이 흔들리지 않도록 Python으로 텍스트 생성을 담당한다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]


def write_text(relative_path: str, content: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8", newline="\n")


def write_backend() -> None:
    write_text(
        "backend/src/main/java/com/aichatbot/global/observability/TraceContext.java",
        """
        package com.aichatbot.global.observability;

        public final class TraceContext {

            private static final ThreadLocal<String> TRACE_ID_HOLDER = new ThreadLocal<>();

            private TraceContext() {
            }

            public static void setTraceId(String traceId) {
                TRACE_ID_HOLDER.set(traceId);
            }

            public static String getTraceId() {
                return TRACE_ID_HOLDER.get();
            }

            public static void clear() {
                TRACE_ID_HOLDER.remove();
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/observability/TraceIdFilter.java",
        """
        package com.aichatbot.global.observability;

        import java.io.IOException;
        import java.util.UUID;
        import jakarta.servlet.FilterChain;
        import jakarta.servlet.ServletException;
        import jakarta.servlet.http.HttpServletRequest;
        import jakarta.servlet.http.HttpServletResponse;
        import org.springframework.core.Ordered;
        import org.springframework.core.annotation.Order;
        import org.springframework.stereotype.Component;
        import org.springframework.web.filter.OncePerRequestFilter;

        @Component
        @Order(Ordered.HIGHEST_PRECEDENCE)
        public class TraceIdFilter extends OncePerRequestFilter {

            @Override
            protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
            ) throws ServletException, IOException {
                // 왜 필요한가: trace_id가 있어야 운영자가 "요청 ~ 응답" 전체 경로를 한 번에 추적할 수 있다.
                String traceId = request.getHeader("X-Trace-Id");
                if (traceId == null || traceId.isBlank()) {
                    traceId = UUID.randomUUID().toString();
                }

                TraceContext.setTraceId(traceId);
                response.setHeader("X-Trace-Id", traceId);

                try {
                    filterChain.doFilter(request, response);
                } finally {
                    TraceContext.clear();
                }
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/tenant/TenantContext.java",
        """
        package com.aichatbot.global.tenant;

        public final class TenantContext {

            private static final ThreadLocal<String> TENANT_KEY_HOLDER = new ThreadLocal<>();

            private TenantContext() {
            }

            public static void setTenantKey(String tenantKey) {
                TENANT_KEY_HOLDER.set(tenantKey);
            }

            public static String getTenantKey() {
                return TENANT_KEY_HOLDER.get();
            }

            public static void clear() {
                TENANT_KEY_HOLDER.remove();
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/tenant/TenantKeyFilter.java",
        """
        package com.aichatbot.global.tenant;

        import com.aichatbot.global.error.ApiErrorResponse;
        import com.aichatbot.global.observability.TraceContext;
        import java.io.IOException;
        import jakarta.servlet.FilterChain;
        import jakarta.servlet.ServletException;
        import jakarta.servlet.http.HttpServletRequest;
        import jakarta.servlet.http.HttpServletResponse;
        import org.springframework.core.Ordered;
        import org.springframework.core.annotation.Order;
        import org.springframework.http.HttpStatus;
        import org.springframework.stereotype.Component;
        import org.springframework.web.filter.OncePerRequestFilter;

        @Component
        @Order(Ordered.HIGHEST_PRECEDENCE + 1)
        public class TenantKeyFilter extends OncePerRequestFilter {

            @Override
            protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
            ) throws ServletException, IOException {
                String tenantKey = request.getHeader("X-Tenant-Key");

                // 왜 필요한가: 테넌트 키가 없으면 데이터가 섞일 수 있으므로 서버에서 즉시 차단한다.
                if (tenantKey == null || tenantKey.isBlank()) {
                    writeBadRequest(response);
                    return;
                }

                TenantContext.setTenantKey(tenantKey.trim());
                try {
                    filterChain.doFilter(request, response);
                } finally {
                    TenantContext.clear();
                }
            }

            private void writeBadRequest(HttpServletResponse response) throws IOException {
                response.setStatus(HttpStatus.BAD_REQUEST.value());
                response.setCharacterEncoding("UTF-8");
                response.setContentType("application/json;charset=UTF-8");

                ApiErrorResponse body = new ApiErrorResponse(
                    "SEC-001-TENANT-KEY-REQUIRED",
                    "X-Tenant-Key 헤더가 필요합니다.",
                    TraceContext.getTraceId()
                );
                response.getWriter().write(toJson(body));
            }

            private String toJson(ApiErrorResponse body) {
                // 왜 필요한가: 빌드 의존성을 최소화하면서도 표준 JSON 에러 형태를 유지하기 위함이다.
                String safeMessage = escapeJson(body.message());
                String safeTraceId = escapeJson(body.traceId() == null ? "" : body.traceId());
                return "{\\"error_code\\":\\"" + body.errorCode() + "\\",\\"message\\":\\"" + safeMessage + "\\",\\"trace_id\\":\\"" + safeTraceId + "\\"}";
            }

            private String escapeJson(String value) {
                return value.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"");
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/error/ApiErrorResponse.java",
        """
        package com.aichatbot.global.error;

        import com.fasterxml.jackson.annotation.JsonProperty;

        public record ApiErrorResponse(
            @JsonProperty("error_code")
            String errorCode,
            String message,
            @JsonProperty("trace_id")
            String traceId
        ) {
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/error/ApiExceptionHandler.java",
        """
        package com.aichatbot.global.error;

        import com.aichatbot.global.observability.TraceContext;
        import org.springframework.http.HttpStatus;
        import org.springframework.http.ResponseEntity;
        import org.springframework.web.bind.annotation.ExceptionHandler;
        import org.springframework.web.bind.annotation.RestControllerAdvice;

        @RestControllerAdvice
        public class ApiExceptionHandler {

            @ExceptionHandler(Exception.class)
            public ResponseEntity<ApiErrorResponse> handleException(Exception exception) {
                // 왜 필요한가: 예외 형태를 통일해야 프론트/운영이 일관되게 대응할 수 있다.
                ApiErrorResponse error = new ApiErrorResponse(
                    "SYS-003-UNEXPECTED",
                    "예상하지 못한 오류가 발생했습니다.",
                    TraceContext.getTraceId()
                );
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/security/SecurityConfig.java",
        """
        package com.aichatbot.global.security;

        import org.springframework.context.annotation.Bean;
        import org.springframework.context.annotation.Configuration;
        import org.springframework.security.config.Customizer;
        import org.springframework.security.config.annotation.web.builders.HttpSecurity;
        import org.springframework.security.config.http.SessionCreationPolicy;
        import org.springframework.security.web.SecurityFilterChain;

        @Configuration
        public class SecurityConfig {

            @Bean
            public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
                // 왜 필요한가: 스켈레톤 단계에서 /health와 데모 API를 바로 확인하기 위해 최소 정책을 둔다.
                http
                    .csrf(csrf -> csrf.disable())
                    .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                    .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/health", "/actuator/health").permitAll()
                        .anyRequest().permitAll()
                    )
                    .httpBasic(Customizer.withDefaults());

                return http.build();
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/global/health/HealthController.java",
        """
        package com.aichatbot.global.health;

        import com.aichatbot.global.observability.TraceContext;
        import java.util.Map;
        import org.springframework.web.bind.annotation.GetMapping;
        import org.springframework.web.bind.annotation.RestController;

        @RestController
        public class HealthController {

            @GetMapping("/health")
            public Map<String, String> health() {
                // 왜 필요한가: 인프라/모니터링이 빠르게 헬스체크를 할 수 있어야 장애를 조기에 탐지한다.
                return Map.of(
                    "status", "UP",
                    "trace_id", TraceContext.getTraceId() == null ? "N/A" : TraceContext.getTraceId()
                );
            }
        }
        """,
    )

    write_text(
        "backend/src/main/java/com/aichatbot/message/presentation/MessageStreamController.java",
        """
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
                String normalized = prompt.replaceAll("\\\\s+", " ").trim();
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
        """,
    )

    write_text(
        "backend/src/main/resources/application.properties",
        """
        spring.application.name=backend
        spring.jackson.property-naming-strategy=SNAKE_CASE

        management.endpoints.web.exposure.include=health,info
        management.endpoint.health.show-details=always

        server.servlet.encoding.charset=UTF-8
        server.servlet.encoding.enabled=true
        server.servlet.encoding.force=true
        """,
    )


def write_frontend() -> None:
    write_text(
        "frontend/src/types/sse.ts",
        """
        export type SseEventType =
            | "token"
            | "tool"
            | "citation"
            | "done"
            | "error"
            | "safe_response"
            | "heartbeat";

        export interface SseMessage {
            id?: string;
            event: SseEventType;
            data: string;
        }
        """,
    )

    write_text(
        "frontend/src/utils/piiMasking.ts",
        """
        export function maskSensitiveText(input: string): string {
            if (!input) {
                return input;
            }

            // 왜 필요한가: UI 로그에 원문 PII가 남으면 화면 캡처/운영 로그로 재유출될 수 있다.
            let masked = input;
            masked = masked.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/gi, "[EMAIL_MASKED]");
            masked = masked.replace(/\\b01[0-9]-?\\d{3,4}-?\\d{4}\\b/g, "[PHONE_MASKED]");
            masked = masked.replace(/\\b\\d{2,3}-\\d{2,4}-\\d{4}\\b/g, "[PHONE_MASKED]");
            masked = masked.replace(/\\b\\d{6,}\\b/g, "[NUMBER_MASKED]");
            return masked;
        }
        """,
    )

    write_text(
        "frontend/src/utils/sseParser.ts",
        """
        import type { SseMessage } from "../types/sse";

        export class SseParser {
            private buffer = "";
            private eventName = "message";
            private eventId: string | undefined;
            private dataLines: string[] = [];

            feed(chunk: string): SseMessage[] {
                this.buffer += chunk;
                const lines = this.buffer.split(/\\r?\\n/);
                this.buffer = lines.pop() ?? "";

                const messages: SseMessage[] = [];
                for (const line of lines) {
                    if (line === "") {
                        const flushed = this.flush();
                        if (flushed) {
                            messages.push(flushed);
                        }
                        continue;
                    }

                    if (line.startsWith("event:")) {
                        this.eventName = line.slice(6).trim();
                        continue;
                    }
                    if (line.startsWith("id:")) {
                        this.eventId = line.slice(3).trim();
                        continue;
                    }
                    if (line.startsWith("data:")) {
                        this.dataLines.push(line.slice(5).trimStart());
                    }
                }
                return messages;
            }

            flush(): SseMessage | null {
                if (this.dataLines.length === 0) {
                    this.eventName = "message";
                    this.eventId = undefined;
                    return null;
                }

                const payload: SseMessage = {
                    id: this.eventId,
                    event: this.eventName as SseMessage["event"],
                    data: this.dataLines.join("\\n"),
                };

                this.eventName = "message";
                this.eventId = undefined;
                this.dataLines = [];
                return payload;
            }
        }
        """,
    )

    write_text(
        "frontend/src/App.tsx",
        """
        import { useMemo, useRef, useState } from "react";
        import type { SseEventType } from "./types/sse";
        import { maskSensitiveText } from "./utils/piiMasking";
        import { SseParser } from "./utils/sseParser";
        import "./index.css";

        interface StreamLog {
            time: string;
            event: SseEventType | "system";
            payload: string;
        }

        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
        const DEFAULT_TENANT_KEY = "demo-tenant";

        function App() {
            const [sessionId, setSessionId] = useState("session-demo-001");
            const [prompt, setPrompt] = useState("배송 지연 환불 기준을 알려줘");
            const [tenantKey, setTenantKey] = useState(DEFAULT_TENANT_KEY);
            const [logs, setLogs] = useState<StreamLog[]>([]);
            const [isStreaming, setIsStreaming] = useState(false);
            const [statusText, setStatusText] = useState("대기");
            const [lastEventId, setLastEventId] = useState<string>("");

            const abortRef = useRef<AbortController | null>(null);
            const retryCountRef = useRef(0);

            const canStart = useMemo(() => {
                return Boolean(sessionId.trim() && prompt.trim() && tenantKey.trim()) && !isStreaming;
            }, [sessionId, prompt, tenantKey, isStreaming]);

            const appendLog = (event: StreamLog["event"], rawPayload: string) => {
                const safePayload = maskSensitiveText(rawPayload);
                setLogs((prev) => [
                    ...prev,
                    {
                        time: new Date().toLocaleTimeString(),
                        event,
                        payload: safePayload,
                    },
                ]);
            };

            const consumeStream = async (resume: boolean) => {
                const controller = new AbortController();
                abortRef.current = controller;
                const parser = new SseParser();
                const encodedPrompt = encodeURIComponent(prompt);
                const endpoint = `${API_BASE_URL}/api/v1/sessions/${encodeURIComponent(sessionId)}/messages/stream?prompt=${encodedPrompt}`;

                setStatusText(resume ? "재연결 중" : "연결 중");
                appendLog("system", `요청 시작: ${endpoint}`);

                const headers: Record<string, string> = {
                    Accept: "text/event-stream",
                    "X-Tenant-Key": tenantKey,
                };
                if (resume && lastEventId) {
                    headers["Last-Event-ID"] = lastEventId;
                }

                const response = await fetch(endpoint, {
                    method: "GET",
                    headers,
                    signal: controller.signal,
                });

                if (!response.ok || !response.body) {
                    const errorText = await response.text();
                    appendLog("error", `HTTP ${response.status}: ${errorText}`);
                    throw new Error(`stream failed: ${response.status}`);
                }

                setStatusText("수신 중");
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let receivedDone = false;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        break;
                    }
                    const chunk = decoder.decode(value, { stream: true });
                    const events = parser.feed(chunk);
                    for (const evt of events) {
                        if (evt.id) {
                            setLastEventId(evt.id);
                        }
                        appendLog(evt.event, evt.data);
                        if (evt.event === "done") {
                            receivedDone = true;
                            setStatusText("완료");
                        }
                    }
                }

                const flushed = parser.flush();
                if (flushed) {
                    appendLog(flushed.event, flushed.data);
                    if (flushed.event === "done") {
                        receivedDone = true;
                        setStatusText("완료");
                    }
                }

                // 왜 필요한가: SSE 연결이 중간에 끊겨도 최소 1회는 이어받아 UX 끊김을 줄인다.
                if (!receivedDone && retryCountRef.current < 1) {
                    retryCountRef.current += 1;
                    setStatusText("연결 끊김 - 1회 재시도");
                    appendLog("system", "done 이벤트를 받지 못해 재연결합니다.");
                    await consumeStream(true);
                }
            };

            const startStreaming = async () => {
                try {
                    setIsStreaming(true);
                    retryCountRef.current = 0;
                    await consumeStream(false);
                } catch (error) {
                    const message = error instanceof Error ? error.message : "알 수 없는 오류";
                    setStatusText("오류");
                    appendLog("error", message);
                } finally {
                    setIsStreaming(false);
                }
            };

            const stopStreaming = () => {
                abortRef.current?.abort();
                setStatusText("중지됨");
                appendLog("system", "사용자가 스트리밍을 중지했습니다.");
                setIsStreaming(false);
            };

            const clearLogs = () => {
                setLogs([]);
            };

            return (
                <main className="page">
                    <section className="panel controls">
                        <h1>CS AI 챗봇 스트리밍 데모</h1>
                        <p className="caption">SSE 이벤트(token/tool/citation/done/error/safe_response)를 확인합니다.</p>
                        <label>
                            Session ID
                            <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} disabled={isStreaming} />
                        </label>
                        <label>
                            Tenant Key
                            <input value={tenantKey} onChange={(e) => setTenantKey(e.target.value)} disabled={isStreaming} />
                        </label>
                        <label>
                            Prompt
                            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={isStreaming} />
                        </label>
                        <div className="actions">
                            <button onClick={startStreaming} disabled={!canStart}>
                                스트리밍 시작
                            </button>
                            <button onClick={stopStreaming} disabled={!isStreaming}>
                                중지
                            </button>
                            <button onClick={clearLogs}>로그 비우기</button>
                        </div>
                        <p className="status">상태: {statusText}</p>
                        <p className="status">Last-Event-ID: {lastEventId || "-"}</p>
                    </section>
                    <section className="panel logs">
                        <h2>스트리밍 로그(PII 마스킹 적용)</h2>
                        <div className="log-list">
                            {logs.length === 0 ? (
                                <p className="empty">아직 로그가 없습니다.</p>
                            ) : (
                                logs.map((log, index) => (
                                    <article key={`${log.time}-${index}`} className={`log-item log-${log.event}`}>
                                        <header>
                                            <strong>{log.event}</strong>
                                            <span>{log.time}</span>
                                        </header>
                                        <pre>{log.payload}</pre>
                                    </article>
                                ))
                            )}
                        </div>
                    </section>
                </main>
            );
        }

        export default App;
        """,
    )

    write_text(
        "frontend/src/main.tsx",
        """
        import { StrictMode } from "react";
        import { createRoot } from "react-dom/client";
        import App from "./App";

        createRoot(document.getElementById("root")!).render(
            <StrictMode>
                <App />
            </StrictMode>,
        );
        """,
    )

    write_text(
        "frontend/src/index.css",
        """
        :root {
            font-family: "Pretendard", "Noto Sans KR", sans-serif;
            color: #0f172a;
            background-color: #f6f8fc;
            line-height: 1.5;
            font-weight: 400;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
        }

        .page {
            display: grid;
            grid-template-columns: minmax(320px, 420px) 1fr;
            gap: 20px;
            padding: 20px;
            min-height: 100vh;
        }

        .panel {
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 12px;
            padding: 16px;
        }

        .controls h1 {
            margin: 0 0 8px;
            font-size: 24px;
        }

        .caption {
            margin: 0 0 16px;
            color: #475569;
        }

        label {
            display: block;
            margin-bottom: 12px;
            font-size: 13px;
            font-weight: 600;
        }

        input,
        textarea {
            width: 100%;
            margin-top: 6px;
            padding: 10px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
        }

        textarea {
            min-height: 90px;
            resize: vertical;
        }

        .actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin: 12px 0;
        }

        button {
            border: none;
            border-radius: 8px;
            padding: 10px 14px;
            cursor: pointer;
            font-weight: 700;
            background: #1e3a8a;
            color: #ffffff;
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .status {
            margin: 4px 0;
            color: #334155;
            font-size: 13px;
        }

        .logs h2 {
            margin-top: 0;
        }

        .log-list {
            max-height: 76vh;
            overflow: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .log-item {
            border-radius: 8px;
            border: 1px solid #dbe3ef;
            padding: 10px;
            background: #f8fbff;
        }

        .log-item header {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 8px;
            color: #334155;
        }

        .log-item pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: "Consolas", "D2Coding", monospace;
            font-size: 13px;
        }

        .log-error {
            border-color: #fecaca;
            background: #fff1f2;
        }

        .log-safe_response {
            border-color: #fcd34d;
            background: #fef9c3;
        }

        .empty {
            color: #64748b;
        }

        @media (max-width: 1024px) {
            .page {
                grid-template-columns: 1fr;
            }
        }
        """,
    )


def write_infra() -> None:
    write_text(
        "infra/docker-compose.yml",
        """
        version: "3.9"
        services:
          postgres:
            image: postgres:16
            container_name: aichatbot-postgres
            restart: unless-stopped
            environment:
              POSTGRES_DB: aichatbot
              POSTGRES_USER: aichatbot
              # 로컬 예시 비밀번호: 운영에서는 환경변수/시크릿 매니저로 반드시 교체해야 합니다.
              POSTGRES_PASSWORD: local-dev-only-password
            ports:
              - "5432:5432"
            volumes:
              - pg_data:/var/lib/postgresql/data
            healthcheck:
              test: ["CMD-SHELL", "pg_isready -U aichatbot -d aichatbot"]
              interval: 10s
              timeout: 5s
              retries: 5

          redis:
            image: redis:7
            container_name: aichatbot-redis
            restart: unless-stopped
            command: redis-server --appendonly yes
            ports:
              - "6379:6379"
            volumes:
              - redis_data:/data
            healthcheck:
              test: ["CMD", "redis-cli", "ping"]
              interval: 10s
              timeout: 5s
              retries: 5

        volumes:
          pg_data:
          redis_data:
        """,
    )


def write_gitignore() -> None:
    write_text(
        ".gitignore",
        """
        # OS
        .DS_Store
        Thumbs.db
        Desktop.ini

        # IDE / Editor
        .idea/
        *.iml
        .vscode/
        !.vscode/extensions.json
        !.vscode/settings.json
        !.vscode/tasks.json
        !.vscode/launch.json

        # Environment / Secrets
        .env
        .env.*
        *.pem
        *.key
        *.p12
        *.jks
        service-account*.json

        # Logs / Temp
        *.log
        *.tmp
        tmp/
        temp/
        out/

        # Backend (Spring/Gradle)
        backend/.gradle/
        backend/build/
        backend/out/
        backend/tmp/
        backend/*.log
        backend/**/*.class
        # 산출 JAR/WAR는 기본 제외. 배포 정책이 생기면 예외 규칙으로 관리하세요.
        backend/**/*.jar
        backend/**/*.war

        # Frontend (Vite/Node)
        frontend/node_modules/
        frontend/dist/
        frontend/.vite/
        frontend/coverage/
        frontend/*.log
        frontend/.env.local
        frontend/*.local

        # Infra local data / dump / backup
        infra/.data/
        infra/data/
        infra/volumes/
        infra/**/*.dump
        infra/**/*.sql
        infra/**/*.bak
        infra/**/*.backup

        # Codex / Agents
        # 기본 정책: 설치된 스킬 결과물은 커밋하지 않는다.
        .agents/skills/
        # 필요 시 팀 정책에 따라 아래 예외를 활성화해 특정 스킬만 고정할 수 있다.
        # !.agents/skills/<skill-name>/
        """,
    )


def write_readme() -> None:
    write_text(
        "README.md",
        """
        # AI_Chatbot (고객센터 서포팅 AI 챗봇)

        이 저장소는 `AGENTS.md` 규칙을 기준으로 구성된 기본 스캐폴딩입니다.  
        핵심 원칙: **Fail-Closed, PII 마스킹, 테넌트 격리, trace_id 전파, 예산/레이트리밋 강제**

        ## 1) 사전 요구사항
        - Windows CMD
        - Git
        - Java 17
        - Node.js + npm
        - Python 3.11+
        - Docker Desktop (선택, 로컬 인프라 실행용)

        ## 2) 루트 이동 (CMD)
        ```cmd
        cd /d "C:\\Users\\hjjmj\\OneDrive\\바탕 화면\\AI_Chatbot"
        ```

        ## 3) 자동화 스크립트 실행 순서 (CMD)
        ```cmd
        00_bootstrap.cmd
        10_generate_backend.cmd
        11_backend_skeleton.cmd
        20_generate_frontend.cmd
        21_frontend_skeleton.cmd
        30_generate_infra.cmd
        40_install_skills.cmd
        50_generate_gitignore.cmd
        60_generate_readme.cmd
        90_verify.cmd
        99_git_init_commit_push.cmd
        ```

        ## 4) 개별 실행 가이드
        - 백엔드 실행:
        ```cmd
        cd /d "C:\\Users\\hjjmj\\OneDrive\\바탕 화면\\AI_Chatbot\\backend"
        gradlew.bat bootRun
        ```

        - 프론트 실행:
        ```cmd
        cd /d "C:\\Users\\hjjmj\\OneDrive\\바탕 화면\\AI_Chatbot\\frontend"
        npm install
        npm run dev
        ```

        - 인프라 실행 (Docker 필요):
        ```cmd
        cd /d "C:\\Users\\hjjmj\\OneDrive\\바탕 화면\\AI_Chatbot"
        docker compose -f "infra\\docker-compose.yml" up -d
        ```

        ## 5) 보안 주의사항
        - `infra/docker-compose.yml`의 비밀번호는 **로컬 예시값**입니다.
        - 운영 환경에서는 반드시 환경변수 + Vault/KMS/Secret Manager를 사용하세요.
        - `.env`, 인증서/키 파일(`*.pem`, `*.key`, `*.p12`, `*.jks`)은 커밋 금지입니다.

        ## 6) 스킬 설치 정책
        - 기본 정책: `.agents/skills`는 커밋하지 않습니다.
        - 설치 명령/성공 여부는 `docs/ops/CODEX_WORKLOG.md`에서 추적합니다.

        ## 7) 운영/품질 기준 요약
        - trace_id: 요청/응답 헤더(`X-Trace-Id`) 전파
        - tenant_key: `X-Tenant-Key` 필수, 누락 시 400
        - 표준 에러 포맷: `{ "error_code", "message", "trace_id" }`
        - SSE 이벤트 타입: `token`, `tool`, `citation`, `done`, `error`, `safe_response`
        - PII는 로그/캐시/UI 노출 금지(마스킹)
        """,
    )


def init_worklog() -> None:
    path = ROOT / "docs/ops/CODEX_WORKLOG.md"
    if path.exists():
        return
    write_text(
        "docs/ops/CODEX_WORKLOG.md",
        """
        # CODEX WORKLOG

        > 실행 환경: Windows CMD 기준
        > 인코딩 정책: UTF-8

        """,
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python tools/scaffold_writer.py [backend|frontend|infra|gitignore|readme|worklog_init]")
        return 1

    action = sys.argv[1].strip().lower()
    if action == "backend":
        write_backend()
    elif action == "frontend":
        write_frontend()
    elif action == "infra":
        write_infra()
    elif action == "gitignore":
        write_gitignore()
    elif action == "readme":
        write_readme()
    elif action == "worklog_init":
        init_worklog()
    else:
        print(f"unknown action: {action}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
