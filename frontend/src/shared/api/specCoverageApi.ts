import { getAuthState } from "../auth/authStore";
import { httpClient } from "./httpClient";
import { buildGeneratedHeaders, generatedApiClient } from "../../api/generated/client";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

type SessionResponse = {
    session_id: string;
    status: string;
    trace_id: string;
};

type MessageAcceptedResponse = {
    id: string;
    session_id: string;
    trace_id: string;
};

type RagAcceptedResponse = {
    id: string;
    trace_id: string;
};

type GeneratedClientResult<T> = {
    data?: T;
    error?: unknown;
    response: Response;
};

function traceId(): string {
    return crypto.randomUUID();
}

function generatedHeaders(includeIdempotencyKey = false): Record<string, string> {
    const auth = getAuthState();
    return buildGeneratedHeaders({
        tenantKey: auth.tenantKey || undefined,
        accessToken: auth.accessToken || undefined,
        includeIdempotencyKey,
    });
}

function unwrapGenerated<T>(result: GeneratedClientResult<T>, endpoint: string): T {
    if (result.response.ok && result.data !== undefined) {
        return result.data;
    }
    const detail =
        typeof result.error === "string" ? result.error : JSON.stringify(result.error ?? {});
    throw new Error(`generated_client_request_failed endpoint=${endpoint} status=${result.response.status} detail=${detail}`);
}

function authHeaders(lastEventId?: string): Headers {
    const auth = getAuthState();
    const headers = new Headers();
    headers.set("X-Trace-Id", traceId());
    if (auth.tenantKey) {
        headers.set("X-Tenant-Key", auth.tenantKey);
    }
    if (auth.accessToken) {
        headers.set("Authorization", `Bearer ${auth.accessToken}`);
    }
    if (lastEventId) {
        headers.set("Last-Event-ID", lastEventId);
    }
    return headers;
}

async function getSseText(urlPath: string, lastEventId?: string): Promise<string> {
    const response = await fetch(`${API_BASE_URL}${urlPath}`, {
        method: "GET",
        headers: authHeaders(lastEventId),
        credentials: "include",
    });
    if (!response.ok) {
        throw new Error(`sse_request_failed status=${response.status}`);
    }
    return response.text();
}

export async function fetchChatBootstrap() {
    const result = await generatedApiClient.GET("/v1/chat/bootstrap", {
        headers: generatedHeaders(),
    });
    return unwrapGenerated<Record<string, unknown>>(
        result as GeneratedClientResult<Record<string, unknown>>,
        "/v1/chat/bootstrap",
    );
}

export async function createConversationSession(): Promise<SessionResponse> {
    const result = await generatedApiClient.POST("/v1/sessions", {
        body: {},
        headers: generatedHeaders(true),
    });
    return unwrapGenerated<SessionResponse>(
        result as GeneratedClientResult<SessionResponse>,
        "/v1/sessions",
    );
}

export async function getConversationSession(sessionId: string): Promise<SessionResponse> {
    const result = await generatedApiClient.GET("/v1/sessions/{session_id}", {
        params: {
            path: {
                session_id: sessionId,
            },
        },
        headers: generatedHeaders(),
    });
    return unwrapGenerated<SessionResponse>(
        result as GeneratedClientResult<SessionResponse>,
        "/v1/sessions/{session_id}",
    );
}

export async function postConversationMessage(
    sessionId: string,
    payload: { text: string; topK?: number },
): Promise<MessageAcceptedResponse> {
    const result = await generatedApiClient.POST("/v1/sessions/{session_id}/messages", {
        params: {
            path: {
                session_id: sessionId,
            },
        },
        body: {
            text: payload.text,
            top_k: payload.topK ?? 3,
            client_nonce: crypto.randomUUID(),
        },
        headers: generatedHeaders(true),
    });
    return unwrapGenerated<MessageAcceptedResponse>(
        result as GeneratedClientResult<MessageAcceptedResponse>,
        "/v1/sessions/{session_id}/messages",
    );
}

export async function listConversationMessages(sessionId: string) {
    const result = await generatedApiClient.GET("/v1/sessions/{session_id}/messages", {
        params: {
            path: {
                session_id: sessionId,
            },
        },
        headers: generatedHeaders(),
    });
    return unwrapGenerated<Record<string, unknown>>(
        result as GeneratedClientResult<Record<string, unknown>>,
        "/v1/sessions/{session_id}/messages",
    );
}

export async function streamConversationMessage(sessionId: string, messageId: string): Promise<string> {
    return getSseText(`/v1/sessions/${sessionId}/messages/${messageId}/stream`);
}

export async function resumeConversationMessage(
    sessionId: string,
    messageId: string,
    lastEventId: string,
): Promise<string> {
    const query = encodeURIComponent(lastEventId);
    const resumePath = `/v1/sessions/${sessionId}/messages/${messageId}/stream/resume`;
    return getSseText(`${resumePath}?last_event_id=${query}`, lastEventId);
}

export async function closeConversationSession(sessionId: string, reason: string) {
    const result = await generatedApiClient.POST("/v1/sessions/{session_id}/close", {
        params: {
            path: {
                session_id: sessionId,
            },
        },
        body: { reason },
        headers: generatedHeaders(true),
    });
    return unwrapGenerated<Record<string, unknown>>(
        result as GeneratedClientResult<Record<string, unknown>>,
        "/v1/sessions/{session_id}/close",
    );
}

export async function retryConversationMessage(sessionId: string, messageId: string, reason: string) {
    const result = await generatedApiClient.POST("/v1/sessions/{session_id}/messages/{message_id}/retry", {
        params: {
            path: {
                session_id: sessionId,
                message_id: messageId,
            },
        },
        body: { reason },
        headers: generatedHeaders(true),
    });
    return unwrapGenerated<Record<string, unknown>>(
        result as GeneratedClientResult<Record<string, unknown>>,
        "/v1/sessions/{session_id}/messages/{message_id}/retry",
    );
}

export async function postQuickReply(sessionId: string, quickReplyId: string, text: string) {
    const response = await httpClient.post(`/v1/sessions/${sessionId}/quick-replies/${quickReplyId}`, { text });
    return response.data;
}

export async function postCsat(sessionId: string, score: number, comment: string) {
    const response = await httpClient.post(`/v1/sessions/${sessionId}/csat`, { score, comment });
    return response.data;
}

export async function requestHandoff(sessionId: string, reason: string) {
    const response = await httpClient.post(`/v1/sessions/${sessionId}/handoff`, { reason });
    return response.data;
}

export async function requestAttachmentPresign(fileName: string, contentType = "text/plain") {
    const response = await httpClient.post("/v1/attachments/presign", {
        file_name: fileName,
        content_type: contentType,
    });
    return response.data;
}

export async function completeAttachment(attachmentId: string) {
    const response = await httpClient.post(`/v1/attachments/${attachmentId}/complete`);
    return response.data;
}

export async function classifyRagQuery(query: string) {
    const response = await httpClient.post("/v1/rag/query/classify", { query });
    return response.data;
}

export async function suggestRagClarify(query: string) {
    const response = await httpClient.post("/v1/rag/clarify/suggest", { query });
    return response.data;
}

export async function requestTemplateRecommendations(sessionId: string, query: string) {
    const response = await httpClient.post(`/v1/sessions/${sessionId}/template-recommendations`, { query });
    return response.data;
}

export async function retrieveRag(query: string, topK = 3): Promise<RagAcceptedResponse> {
    const response = await httpClient.post<RagAcceptedResponse>("/v1/rag/retrieve", {
        query,
        top_k: topK,
    });
    return response.data;
}

export async function answerRag(query: string, topK = 3): Promise<RagAcceptedResponse | Record<string, unknown>> {
    const response = await httpClient.post<RagAcceptedResponse | Record<string, unknown>>("/v1/rag/answer", {
        query,
        top_k: topK,
        answer_contract: {
            schema_version: "v1",
            citation_required: true,
            fail_closed: true,
        },
    });
    return response.data;
}

export async function listRagCitations(answerId: string) {
    const response = await httpClient.get(`/v1/rag/answers/${answerId}/citations`, {
        params: { limit: 10 },
    });
    return response.data;
}

export async function fetchWorkflowReport() {
    const response = await httpClient.get("/v1/ops/workflow/reports");
    return response.data;
}

export async function fetchMcpServerHealth(serverId: string) {
    const response = await httpClient.get(`/v1/ops/mcp/servers/${serverId}/health`);
    return response.data;
}

export async function fetchTenantUsageReport(tenantId: string) {
    const response = await httpClient.get(`/v1/admin/tenants/${tenantId}/usage-report`, {
        params: {
            include_quota: true,
        },
    });
    return response.data;
}

export async function upsertTenantQuota(tenantId: string, payload: {
    maxQps: number;
    maxDailyTokens: number;
    maxMonthlyCost: number;
}) {
    const effectiveFrom = new Date().toISOString();
    const response = await httpClient.put(
        `/v1/admin/tenants/${tenantId}/quota`,
        {
            max_qps: payload.maxQps,
            max_daily_tokens: payload.maxDailyTokens,
            max_monthly_cost: payload.maxMonthlyCost,
            effective_from: effectiveFrom,
            breach_action: "BLOCK",
        },
        {
            headers: {
                "Idempotency-Key": crypto.randomUUID(),
            },
        },
    );
    return response.data;
}
