import { useMemo, useRef, useState } from "react";
import type { SseEventType } from "./types/sse";
import { maskSensitiveText } from "./utils/piiMasking";
import { SseParser } from "./utils/sseParser";
import "./index.css";

type ChatMessage = {
    id: string;
    role: "AGENT" | "ASSISTANT";
    text: string;
};

type CitationItem = {
    citation_id: string;
    chunk_id: string;
    rank_no: number;
    excerpt_masked: string;
};

type ErrorBanner = {
    errorCode: string;
    message: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

function App() {
    const [tenantKey, setTenantKey] = useState("demo-tenant");
    const [loginId, setLoginId] = useState("agent1");
    const [password, setPassword] = useState("agent1-pass");
    const [accessToken, setAccessToken] = useState("");
    const [sessionId, setSessionId] = useState("");
    const [prompt, setPrompt] = useState("Explain delayed shipping refund policy.");
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [citations, setCitations] = useState<CitationItem[]>([]);
    const [safeBanner, setSafeBanner] = useState("");
    const [errorBanner, setErrorBanner] = useState<ErrorBanner | null>(null);
    const [isStreaming, setIsStreaming] = useState(false);
    const [statusText, setStatusText] = useState("Login required");

    const parserRef = useRef(new SseParser());
    const lastEventIdRef = useRef("0");
    const seenEventIdsRef = useRef<Set<string>>(new Set());

    const canLogin = useMemo(() => {
        return Boolean(tenantKey.trim() && loginId.trim() && password.trim());
    }, [tenantKey, loginId, password]);

    const canSend = useMemo(() => {
        return Boolean(accessToken && sessionId && prompt.trim()) && !isStreaming;
    }, [accessToken, sessionId, prompt, isStreaming]);

    const commonHeaders = (includeAuth = true): Record<string, string> => {
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
            "X-Tenant-Key": tenantKey,
            "X-Trace-Id": crypto.randomUUID(),
        };
        if (includeAuth && accessToken) {
            headers.Authorization = `Bearer ${accessToken}`;
        }
        return headers;
    };

    const login = async () => {
        setErrorBanner(null);
        setStatusText("Logging in");
        try {
            const loginRes = await fetch(`${API_BASE_URL}/v1/auth/login`, {
                method: "POST",
                headers: {
                    ...commonHeaders(false),
                    "Idempotency-Key": crypto.randomUUID(),
                },
                body: JSON.stringify({
                    login_id: loginId,
                    password,
                    channel_id: "agent-console",
                    client_nonce: crypto.randomUUID(),
                }),
            });

            const loginJson = await loginRes.json();
            if (!loginRes.ok) {
                setErrorBanner({
                    errorCode: loginJson.error_code ?? "SYS-003-500",
                    message: loginJson.message ?? "Login failed",
                });
                setStatusText("Login failed");
                return;
            }

            setAccessToken(loginJson.access_token);

            await fetch(`${API_BASE_URL}/v1/chat/bootstrap`, {
                method: "GET",
                headers: {
                    ...commonHeaders(true),
                    Authorization: `Bearer ${loginJson.access_token}`,
                },
            });

            const sessionRes = await fetch(`${API_BASE_URL}/v1/sessions`, {
                method: "POST",
                headers: {
                    ...commonHeaders(true),
                    Authorization: `Bearer ${loginJson.access_token}`,
                    "Idempotency-Key": crypto.randomUUID(),
                },
                body: JSON.stringify({ reason: "agent_console_login" }),
            });

            const sessionJson = await sessionRes.json();
            if (!sessionRes.ok) {
                setErrorBanner({
                    errorCode: sessionJson.error_code ?? "SYS-003-500",
                    message: sessionJson.message ?? "Session creation failed",
                });
                setStatusText("Session creation failed");
                return;
            }

            setSessionId(sessionJson.session_id);
            setMessages([]);
            setCitations([]);
            setSafeBanner("");
            setStatusText("Ready");
        } catch (error) {
            setErrorBanner({
                errorCode: "SYS-003-500",
                message: error instanceof Error ? error.message : "Login error",
            });
            setStatusText("Error");
        }
    };

    const sendQuestion = async () => {
        setErrorBanner(null);
        setSafeBanner("");
        setCitations([]);

        const questionText = prompt.trim();
        const tempAssistantId = `assistant-${crypto.randomUUID()}`;
        setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "AGENT", text: maskSensitiveText(questionText) },
            { id: tempAssistantId, role: "ASSISTANT", text: "" },
        ]);

        setIsStreaming(true);
        setStatusText("Posting message");
        seenEventIdsRef.current = new Set();
        lastEventIdRef.current = "0";
        parserRef.current = new SseParser();

        try {
            const postRes = await fetch(`${API_BASE_URL}/v1/sessions/${sessionId}/messages`, {
                method: "POST",
                headers: {
                    ...commonHeaders(true),
                    "Idempotency-Key": crypto.randomUUID(),
                },
                body: JSON.stringify({
                    text: questionText,
                    client_nonce: crypto.randomUUID(),
                }),
            });

            const postJson = await postRes.json();
            if (!postRes.ok) {
                setErrorBanner({
                    errorCode: postJson.error_code ?? "SYS-003-500",
                    message: postJson.message ?? "Message post failed",
                });
                setStatusText("Post failed");
                setIsStreaming(false);
                return;
            }

            const answerId: string = postJson.id;
            const done = await streamAnswer(answerId, tempAssistantId, false);
            if (!done) {
                await streamAnswer(answerId, tempAssistantId, true);
            }
        } catch (error) {
            setErrorBanner({
                errorCode: "SYS-003-500",
                message: error instanceof Error ? error.message : "Streaming error",
            });
            setStatusText("Error");
        } finally {
            setIsStreaming(false);
        }
    };

    const streamAnswer = async (messageId: string, tempAssistantId: string, resume: boolean): Promise<boolean> => {
        const endpoint = resume
            ? `${API_BASE_URL}/v1/sessions/${sessionId}/messages/${messageId}/stream/resume`
            : `${API_BASE_URL}/v1/sessions/${sessionId}/messages/${messageId}/stream`;

        const headers: Record<string, string> = {
            ...commonHeaders(true),
            Accept: "text/event-stream",
        };
        delete headers["Content-Type"];

        if (resume && lastEventIdRef.current && lastEventIdRef.current !== "0") {
            headers["Last-Event-ID"] = lastEventIdRef.current;
        }

        const streamRes = await fetch(endpoint, {
            method: "GET",
            headers,
        });

        if (!streamRes.ok || !streamRes.body) {
            const text = await streamRes.text();
            const parsed = tryParseJson(text);
            setErrorBanner({
                errorCode: parsed?.error_code ?? "SYS-003-500",
                message: parsed?.message ?? "Stream connect failed",
            });
            setStatusText("Stream failed");
            return true;
        }

        setStatusText(resume ? "Receiving resumed stream" : "Receiving stream");

        const reader = streamRes.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let receivedDone = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            const chunk = decoder.decode(value, { stream: true });
            const events = parserRef.current.feed(chunk);
            for (const event of events) {
                if (event.id) {
                    if (seenEventIdsRef.current.has(event.id)) {
                        continue;
                    }
                    seenEventIdsRef.current.add(event.id);
                    lastEventIdRef.current = event.id;
                }
                handleSseEvent(event.event, event.data, tempAssistantId);
                if (event.event === "done") {
                    receivedDone = true;
                }
            }
        }

        const flushed = parserRef.current.flush();
        if (flushed) {
            if (!flushed.id || !seenEventIdsRef.current.has(flushed.id)) {
                if (flushed.id) {
                    seenEventIdsRef.current.add(flushed.id);
                    lastEventIdRef.current = flushed.id;
                }
                handleSseEvent(flushed.event, flushed.data, tempAssistantId);
                if (flushed.event === "done") {
                    receivedDone = true;
                }
            }
        }

        return receivedDone;
    };

    const handleSseEvent = (eventType: SseEventType, rawData: string, tempAssistantId: string) => {
        const parsed = tryParseJson(rawData);

        if (eventType === "token") {
            const text = maskSensitiveText(parsed?.text ?? "");
            setMessages((prev) =>
                prev.map((message) =>
                    message.id === tempAssistantId ? { ...message, text: `${message.text}${text}` } : message,
                ),
            );
            return;
        }

        if (eventType === "citation") {
            setCitations((prev) => [
                ...prev,
                {
                    citation_id: parsed?.citation_id ?? crypto.randomUUID(),
                    chunk_id: parsed?.chunk_id ?? "unknown",
                    rank_no: parsed?.rank_no ?? prev.length + 1,
                    excerpt_masked: maskSensitiveText(parsed?.excerpt_masked ?? ""),
                },
            ]);
            return;
        }

        if (eventType === "safe_response") {
            setSafeBanner(parsed?.message ?? "Switched to safe response.");
            return;
        }

        if (eventType === "error") {
            setErrorBanner({
                errorCode: parsed?.error_code ?? "SYS-003-500",
                message: parsed?.message ?? "Stream error",
            });
            return;
        }

        if (eventType === "done") {
            setStatusText("Done");
        }
    };

    return (
        <main className="page">
            <section className="panel controls">
                <h1>Agent Console MVP</h1>
                <p className="caption">Login, create session, ask question, and validate stream events.</p>

                <label>
                    Tenant Key
                    <input value={tenantKey} onChange={(event) => setTenantKey(event.target.value)} />
                </label>
                <label>
                    Login ID
                    <input value={loginId} onChange={(event) => setLoginId(event.target.value)} />
                </label>
                <label>
                    Password
                    <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
                </label>
                <div className="actions">
                    <button onClick={login} disabled={!canLogin || isStreaming}>
                        Login
                    </button>
                </div>

                <label>
                    Session ID
                    <input value={sessionId} disabled />
                </label>
                <label>
                    Question
                    <textarea
                        value={prompt}
                        onChange={(event) => setPrompt(event.target.value)}
                        disabled={!accessToken || isStreaming}
                    />
                </label>

                <div className="actions">
                    <button onClick={sendQuestion} disabled={!canSend}>
                        Send Question
                    </button>
                </div>

                <p className="status">Status: {statusText}</p>
                {safeBanner && <p className="status log-safe_response">SAFE: {safeBanner}</p>}
                {errorBanner && (
                    <p className="status log-error">
                        {errorBanner.errorCode}: {errorBanner.message}
                    </p>
                )}
            </section>

            <section className="panel logs">
                <h2>Conversation</h2>
                <div className="log-list">
                    {messages.map((message) => (
                        <article key={message.id} className="log-item">
                            <header>
                                <strong>{message.role}</strong>
                            </header>
                            <pre>{maskSensitiveText(message.text)}</pre>
                        </article>
                    ))}
                    {messages.length === 0 && <p className="empty">No messages yet.</p>}
                </div>

                <h2>Evidence Panel</h2>
                <div className="log-list">
                    {citations.map((citation) => (
                        <article key={citation.citation_id} className="log-item">
                            <header>
                                <strong>#{citation.rank_no}</strong>
                                <span>{citation.chunk_id}</span>
                            </header>
                            <pre>{citation.excerpt_masked}</pre>
                        </article>
                    ))}
                    {citations.length === 0 && <p className="empty">No citations yet.</p>}
                </div>
            </section>
        </main>
    );
}

function tryParseJson(raw: string): Record<string, any> | null {
    try {
        return JSON.parse(raw) as Record<string, any>;
    } catch {
        return null;
    }
}

export default App;
