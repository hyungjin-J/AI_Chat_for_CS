import { useMemo, useState } from "react";
import {
    answerRag,
    classifyRagQuery,
    closeConversationSession,
    completeAttachment,
    createConversationSession,
    fetchChatBootstrap,
    fetchMcpServerHealth,
    fetchTenantUsageReport,
    fetchWorkflowReport,
    getConversationSession,
    listConversationMessages,
    listRagCitations,
    postConversationMessage,
    postCsat,
    postQuickReply,
    requestAttachmentPresign,
    requestHandoff,
    requestTemplateRecommendations,
    resumeConversationMessage,
    retryConversationMessage,
    retrieveRag,
    streamConversationMessage,
    suggestRagClarify,
    upsertTenantQuota,
} from "../../../../shared/api/specCoverageApi";
import { getAuthState, hasAnyRole } from "../../../../shared/auth/authStore";
import { SectionPanel } from "../../../../widgets";

function toPretty(value: unknown): string {
    if (typeof value === "string") {
        return value;
    }
    return JSON.stringify(value, null, 2);
}

export function SpecCoverageOperationsView() {
    const auth = getAuthState();
    const canAgentActions = hasAnyRole("AGENT");
    const canOpsActions = hasAnyRole("OPS", "ADMIN");
    const canAdminActions = hasAnyRole("ADMIN");

    const [sessionId, setSessionId] = useState("");
    const [messageId, setMessageId] = useState("");
    const [answerId, setAnswerId] = useState("");
    const [attachmentId, setAttachmentId] = useState("");
    const [serverId, setServerId] = useState("default");
    const [messageText, setMessageText] = useState("refund policy request");
    const [ragQuery, setRagQuery] = useState("refund policy");
    const [lastEventId, setLastEventId] = useState("3");
    const [quickReplyId, setQuickReplyId] = useState<string>(crypto.randomUUID());
    const [quotaQps, setQuotaQps] = useState("50");
    const [quotaDailyTokens, setQuotaDailyTokens] = useState("100000");
    const [quotaMonthlyCost, setQuotaMonthlyCost] = useState("100.00");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState("");

    const tenantId = useMemo(() => auth.tenantKey || "demo-tenant", [auth.tenantKey]);

    const runAction = async (label: string, action: () => Promise<unknown>) => {
        setLoading(true);
        setError("");
        try {
            const payload = await action();
            setResult(`${label}\n${toPretty(payload)}`);
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "request_failed")
                : "request_failed";
            setError(`${label}: ${message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <SectionPanel
            title="Spec Coverage Operations"
            subtitle="Minimal FE wiring for Must endpoint traceability and role-guarded actions."
        >
            <div className="inline-form">
                <label>
                    Session ID
                    <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
                </label>
                <label>
                    Message ID
                    <input value={messageId} onChange={(event) => setMessageId(event.target.value)} />
                </label>
                <label>
                    Answer ID
                    <input value={answerId} onChange={(event) => setAnswerId(event.target.value)} />
                </label>
                <label>
                    Attachment ID
                    <input value={attachmentId} onChange={(event) => setAttachmentId(event.target.value)} />
                </label>
            </div>

            <h3>Session / Message (AGENT)</h3>
            {!canAgentActions && <p className="hint">AGENT role required. Buttons are disabled by role guard.</p>}
            <div className="toolbar">
                <button disabled={loading || !canAgentActions} onClick={() => void runAction("bootstrap", fetchChatBootstrap)}>Bootstrap</button>
                <button
                    disabled={loading || !canAgentActions}
                    onClick={() => void runAction("create_session", async () => {
                        const data = await createConversationSession();
                        setSessionId(data.session_id);
                        return data;
                    })}
                >
                    Create Session
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("get_session", () => getConversationSession(sessionId))}
                >
                    Get Session
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("list_messages", () => listConversationMessages(sessionId))}
                >
                    List Messages
                </button>
            </div>
            <div className="inline-form">
                <label>
                    Message Text
                    <input value={messageText} onChange={(event) => setMessageText(event.target.value)} />
                </label>
                <label>
                    Quick Reply ID
                    <input value={quickReplyId} onChange={(event) => setQuickReplyId(event.target.value)} />
                </label>
                <label>
                    Last Event ID
                    <input value={lastEventId} onChange={(event) => setLastEventId(event.target.value)} />
                </label>
            </div>
            <div className="toolbar">
                <button
                    disabled={loading || !canAgentActions || !sessionId || !messageText}
                    onClick={() => void runAction("post_message", async () => {
                        const data = await postConversationMessage(sessionId, { text: messageText, topK: 3 });
                        setMessageId(data.id);
                        return data;
                    })}
                >
                    Post Message
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId || !messageId}
                    onClick={() => void runAction("stream_sse", () => streamConversationMessage(sessionId, messageId))}
                >
                    Stream SSE
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId || !messageId}
                    onClick={() => void runAction("stream_resume", () => resumeConversationMessage(sessionId, messageId, lastEventId))}
                >
                    Resume SSE
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("session_close", () => closeConversationSession(sessionId, "manual_close"))}
                >
                    Session Close
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId || !messageId}
                    onClick={() => void runAction("message_retry", () => retryConversationMessage(sessionId, messageId, "manual_retry"))}
                >
                    Message Retry
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId || !quickReplyId}
                    onClick={() => void runAction("quick_reply", () => postQuickReply(sessionId, quickReplyId, "Thanks, confirmed."))}
                >
                    Quick Reply
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("csat", () => postCsat(sessionId, 5, "satisfied"))}
                >
                    Post CSAT
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("handoff", () => requestHandoff(sessionId, "handoff_needed"))}
                >
                    Request Handoff
                </button>
                <button
                    disabled={loading || !canAgentActions || !sessionId}
                    onClick={() => void runAction("template_recommendations", () => requestTemplateRecommendations(sessionId, messageText))}
                >
                    Template Recommend
                </button>
            </div>

            <h3>Attachment / RAG (AGENT)</h3>
            {!canAgentActions && <p className="hint">AGENT role required. Buttons are disabled by role guard.</p>}
            <div className="inline-form">
                <label>
                    RAG Query
                    <input value={ragQuery} onChange={(event) => setRagQuery(event.target.value)} />
                </label>
                <label>
                    MCP Server ID
                    <input value={serverId} onChange={(event) => setServerId(event.target.value)} />
                </label>
            </div>
            <div className="toolbar">
                <button
                    disabled={loading || !canAgentActions}
                    onClick={() => void runAction("attachment_presign", async () => {
                        const data = await requestAttachmentPresign("spec-cover.txt");
                        const nextAttachmentId = typeof data === "object" && data && "attachment_id" in data
                            ? String((data as { attachment_id?: string }).attachment_id ?? "")
                            : "";
                        if (nextAttachmentId) {
                            setAttachmentId(nextAttachmentId);
                        }
                        return data;
                    })}
                >
                    Attachment Presign
                </button>
                <button
                    disabled={loading || !canAgentActions || !attachmentId}
                    onClick={() => void runAction("attachment_complete", () => completeAttachment(attachmentId))}
                >
                    Attachment Complete
                </button>
                <button
                    disabled={loading || !canAgentActions || !ragQuery}
                    onClick={() => void runAction("rag_query_classify", () => classifyRagQuery(ragQuery))}
                >
                    Query Classify
                </button>
                <button
                    disabled={loading || !canAgentActions || !ragQuery}
                    onClick={() => void runAction("rag_clarify_suggest", () => suggestRagClarify(ragQuery))}
                >
                    Clarify Suggest
                </button>
                <button
                    disabled={loading || !canAgentActions || !ragQuery}
                    onClick={() => void runAction("rag_retrieve", async () => {
                        const data = await retrieveRag(ragQuery, 3);
                        setAnswerId(data.id);
                        return data;
                    })}
                >
                    RAG Retrieve
                </button>
                <button
                    disabled={loading || !canAgentActions || !ragQuery}
                    onClick={() => void runAction("rag_answer", async () => {
                        const data = await answerRag(ragQuery, 3);
                        if (typeof data === "object" && data && "id" in data) {
                            setAnswerId(String((data as { id?: string }).id ?? ""));
                        }
                        return data;
                    })}
                >
                    RAG Answer
                </button>
                <button
                    disabled={loading || !canAgentActions || !answerId}
                    onClick={() => void runAction("rag_citations", () => listRagCitations(answerId))}
                >
                    RAG Citations
                </button>
            </div>

            <h3>Ops / Admin</h3>
            {!canOpsActions && <p className="hint">OPS or ADMIN role required. Buttons are disabled by role guard.</p>}
            <div className="inline-form">
                <label>
                    Quota QPS
                    <input value={quotaQps} onChange={(event) => setQuotaQps(event.target.value)} />
                </label>
                <label>
                    Daily Tokens
                    <input value={quotaDailyTokens} onChange={(event) => setQuotaDailyTokens(event.target.value)} />
                </label>
                <label>
                    Monthly Cost
                    <input value={quotaMonthlyCost} onChange={(event) => setQuotaMonthlyCost(event.target.value)} />
                </label>
            </div>
            <div className="toolbar">
                <button
                    disabled={loading || !canOpsActions}
                    onClick={() => void runAction("workflow_report", fetchWorkflowReport)}
                >
                    Workflow Report
                </button>
                <button
                    disabled={loading || !canOpsActions || !serverId}
                    onClick={() => void runAction("mcp_server_health", () => fetchMcpServerHealth(serverId))}
                >
                    MCP Health
                </button>
                <button
                    disabled={loading || !canOpsActions}
                    onClick={() => void runAction("tenant_usage_report", () => fetchTenantUsageReport(tenantId))}
                >
                    Tenant Billing Report
                </button>
                <button
                    disabled={loading || !canAdminActions}
                    onClick={() => void runAction("tenant_quota_upsert", () => upsertTenantQuota(tenantId, {
                        maxQps: Number(quotaQps || "0"),
                        maxDailyTokens: Number(quotaDailyTokens || "0"),
                        maxMonthlyCost: Number(quotaMonthlyCost || "0"),
                    }))}
                >
                    Tenant Quota Upsert
                </button>
            </div>

            {error && <p className="error">{error}</p>}
            <label>
                Last Response
                <textarea className="result-box" value={result} readOnly rows={14} />
            </label>
        </SectionPanel>
    );
}
