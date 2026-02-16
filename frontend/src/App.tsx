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
