import { httpClient } from "./httpClient";

export type DashboardSummaryResponse = {
    tenant_id: string;
    totals: Record<string, number>;
    trace_id: string;
};

export type DashboardSeriesPoint = {
    hour_bucket_utc: string;
    metric_key: string;
    metric_value: number;
};

export type DashboardSeriesResponse = {
    tenant_id: string;
    series: DashboardSeriesPoint[];
    trace_id: string;
};

export type AuditLogItem = {
    audit_id: string;
    action_type: string;
    actor_user_id?: string | null;
    actor_role?: string | null;
    target_type?: string | null;
    target_id?: string | null;
    trace_id: string;
    created_at: string;
};

export type AuditSearchResponse = {
    tenant_id: string;
    items: AuditLogItem[];
    trace_id: string;
};

export type AuditDiffResponse = {
    audit_id: string;
    before_json: string;
    after_json: string;
    source_trace_id: string;
    trace_id: string;
};

export type AuditExportJobCreateRequest = {
    format: "json" | "csv";
    from_utc?: string;
    to_utc?: string;
    row_limit?: number;
    max_bytes?: number;
    max_duration_sec?: number;
};

export type AuditExportJobCreateResponse = {
    job_id: string;
    status: "PENDING" | "RUNNING" | "DONE" | "FAILED" | "EXPIRED";
    expires_at: string;
    trace_id: string;
};

export type AuditExportJobStatusResponse = {
    job_id: string;
    status: "PENDING" | "RUNNING" | "DONE" | "FAILED" | "EXPIRED";
    format: "json" | "csv";
    row_count: number;
    total_bytes: number;
    error_code?: string | null;
    error_message?: string | null;
    created_at: string;
    completed_at?: string | null;
    expires_at: string;
    trace_id: string;
};

export type KbDocumentItem = {
    document_id: string;
    title: string;
    source_type: string;
    category: string;
    effective_date?: string | null;
    owner: string;
    version_no: number;
    status: string;
    approved_at?: string | null;
    updated_at: string;
    trace_id: string;
};

export type KbDocumentListResponse = {
    items: KbDocumentItem[];
    limit: number;
    offset: number;
    trace_id: string;
};

export type KbReindexJobResponse = {
    job_id: string;
    status: string;
    requested_by?: string | null;
    requested_at: string;
    started_at?: string | null;
    completed_at?: string | null;
    result_message?: string | null;
    trace_id: string;
};

export type KbReindexOperationListResponse = {
    items: KbReindexJobResponse[];
    limit: number;
    trace_id: string;
};

export type AdminResourceResponse = {
    resource_key: string;
    status: string;
    active_flag: boolean;
    payload_json?: string | null;
    last_rotated_at?: string | null;
    updated_at: string;
    trace_id: string;
};

export type AdminResourceListResponse = {
    items: AdminResourceResponse[];
    trace_id: string;
};

export async function fetchDashboardSummary(params: {
    tenantId?: string;
    fromUtc?: string;
    toUtc?: string;
}): Promise<DashboardSummaryResponse> {
    const response = await httpClient.get<DashboardSummaryResponse>("/v1/admin/dashboard/summary", {
        params: {
            tenant_id: params.tenantId,
            from_utc: params.fromUtc,
            to_utc: params.toUtc,
        },
    });
    return response.data;
}

export async function fetchDashboardSeries(params: {
    tenantId?: string;
    fromUtc?: string;
    toUtc?: string;
}): Promise<DashboardSeriesResponse> {
    const response = await httpClient.get<DashboardSeriesResponse>("/v1/admin/dashboard/series", {
        params: {
            tenant_id: params.tenantId,
            from_utc: params.fromUtc,
            to_utc: params.toUtc,
        },
    });
    return response.data;
}

export async function fetchAuditLogs(params: {
    tenantId?: string;
    fromUtc?: string;
    toUtc?: string;
    actionType?: string;
    traceId?: string;
}): Promise<AuditSearchResponse> {
    const response = await httpClient.get<AuditSearchResponse>("/v1/admin/audit-logs", {
        params: {
            tenant_id: params.tenantId,
            from_utc: params.fromUtc,
            to_utc: params.toUtc,
            action_type: params.actionType,
            trace_id: params.traceId,
        },
    });
    return response.data;
}

export async function fetchAuditDiff(auditId: string): Promise<AuditDiffResponse> {
    const response = await httpClient.get<AuditDiffResponse>(`/v1/admin/audit-logs/${auditId}/diff`);
    return response.data;
}

export async function uploadKbDocument(payload: {
    title: string;
    sourceType?: string;
    category?: string;
    effectiveDate?: string;
    owner?: string;
}): Promise<KbDocumentItem> {
    const response = await httpClient.post<KbDocumentItem>("/v1/admin/kb/documents", {
        title: payload.title,
        source_type: payload.sourceType,
        category: payload.category,
        effective_date: payload.effectiveDate,
        owner: payload.owner,
    });
    return response.data;
}

export async function listKbDocuments(params?: {
    status?: string;
    limit?: number;
    offset?: number;
}): Promise<KbDocumentListResponse> {
    const response = await httpClient.get<KbDocumentListResponse>("/v1/admin/kb/documents", {
        params: {
            status: params?.status,
            limit: params?.limit,
            offset: params?.offset,
        },
    });
    return response.data;
}

export async function approveKbDocument(documentId: string) {
    const response = await httpClient.post(`/v1/admin/kb/documents/${documentId}/approve`);
    return response.data;
}

export async function rollbackKbDocumentVersion(documentId: string, version: number) {
    const response = await httpClient.post(`/v1/admin/kb/documents/${documentId}/versions/${version}/rollback`);
    return response.data;
}

export async function requestKbReindex(note?: string): Promise<KbReindexJobResponse> {
    const response = await httpClient.post<KbReindexJobResponse>("/v1/admin/kb/reindex", {
        note: note ?? "",
    });
    return response.data;
}

export async function getKbReindexStatus(jobId: string): Promise<KbReindexJobResponse> {
    const response = await httpClient.get<KbReindexJobResponse>(`/v1/admin/kb/reindex/${jobId}`);
    return response.data;
}

export async function listKbIndexOperations(limit = 20): Promise<KbReindexOperationListResponse> {
    const response = await httpClient.get<KbReindexOperationListResponse>("/v1/admin/kb/index-operations", {
        params: { limit },
    });
    return response.data;
}

export async function listTemplates(limit = 50, offset = 0): Promise<AdminResourceListResponse> {
    const response = await httpClient.get<AdminResourceListResponse>("/v1/admin/templates", {
        params: { limit, offset },
    });
    return response.data;
}

export async function createTemplate(payload: { name: string; body?: string }): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>("/v1/admin/templates", payload);
    return response.data;
}

export async function approveTemplate(templateId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/templates/${templateId}/approve`);
    return response.data;
}

export async function deployTemplate(templateId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/templates/${templateId}/deploy`);
    return response.data;
}

export async function rollbackTemplate(templateId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/templates/${templateId}/rollback`);
    return response.data;
}

export async function updatePolicy(policyId: string, payload: Record<string, unknown>): Promise<AdminResourceResponse> {
    const response = await httpClient.put<AdminResourceResponse>(`/v1/admin/policies/${policyId}`, payload);
    return response.data;
}

export async function listModels(limit = 50, offset = 0): Promise<AdminResourceListResponse> {
    const response = await httpClient.get<AdminResourceListResponse>("/v1/admin/models", {
        params: { limit, offset },
    });
    return response.data;
}

export async function createModel(payload: { provider: string; modelName: string }): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>("/v1/admin/models", payload);
    return response.data;
}

export async function activateModel(modelId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/models/${modelId}/activate`);
    return response.data;
}

export async function rollbackModel(modelId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/models/${modelId}/rollback`);
    return response.data;
}

export async function upsertRoutingRule(ruleId: string, payload: Record<string, unknown>): Promise<AdminResourceResponse> {
    const response = await httpClient.put<AdminResourceResponse>(`/v1/admin/routing-rules/${ruleId}`, payload);
    return response.data;
}

export async function testRoutingRule(payload: { ruleId?: string; prompt?: string }) {
    const response = await httpClient.post("/v1/admin/routing-rules/test", payload);
    return response.data;
}

export async function upsertProviderKey(provider: string, secretRef: string): Promise<AdminResourceResponse> {
    const response = await httpClient.put<AdminResourceResponse>(`/v1/admin/provider-keys/${provider}`, {
        secret_ref: secretRef,
    });
    return response.data;
}

export async function rotateProviderKey(provider: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/provider-keys/${provider}/rotate`);
    return response.data;
}

export async function bindProviderSecretRef(providerId: string, secretRef: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/providers/${providerId}/secret-ref`, {
        secret_ref: secretRef,
    });
    return response.data;
}

export async function listProviderHealth() {
    const response = await httpClient.get("/v1/ops/llm/providers/health");
    return response.data;
}

export async function setProviderKillSwitch(provider: string, enabled: boolean): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/ops/llm/providers/${provider}/kill-switch`, {
        enabled,
    });
    return response.data;
}

export async function queryOpsTraces(params?: { keyword?: string; from?: string; to?: string; limit?: number; offset?: number }) {
    const response = await httpClient.get("/v1/ops/traces", {
        params: params ?? {},
    });
    return response.data;
}

export async function fetchOpsMetricSummary(params?: { fromUtc?: string; toUtc?: string }) {
    const response = await httpClient.get("/v1/ops/metrics/summary", {
        params: {
            from_utc: params?.fromUtc,
            to_utc: params?.toUtc,
        },
    });
    return response.data;
}

export async function ingestOpsEvent(payload: { eventType: string; metricKey: string; metricValue?: number; dimensions?: Record<string, unknown> }) {
    const response = await httpClient.post("/v1/internal/events/ingest", {
        event_type: payload.eventType,
        metric_key: payload.metricKey,
        metric_value: payload.metricValue ?? 1,
        dimensions: payload.dimensions ?? {},
    });
    return response.data;
}

export async function triggerOpsRollback(payload: { targetType: string; targetId: string; reason?: string }) {
    const response = await httpClient.post("/v1/ops/rollbacks", {
        target_type: payload.targetType,
        target_id: payload.targetId,
        reason: payload.reason ?? "",
    });
    return response.data;
}

export async function listVersionBundles(limit = 50, offset = 0): Promise<AdminResourceListResponse> {
    const response = await httpClient.get<AdminResourceListResponse>("/v1/admin/version-bundles", {
        params: { limit, offset },
    });
    return response.data;
}

export async function activateVersionBundle(bundleId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/version-bundles/${bundleId}/activate`);
    return response.data;
}

export async function rollbackVersionBundle(bundleId: string): Promise<AdminResourceResponse> {
    const response = await httpClient.post<AdminResourceResponse>(`/v1/admin/version-bundles/${bundleId}/rollback`);
    return response.data;
}

export async function upsertRbacMatrix(resourceKey: string, payload: { roleCode: string; adminLevel: string; allowed: boolean }) {
    const response = await httpClient.put(`/v1/admin/rbac/matrix/${resourceKey}`, {
        role_code: payload.roleCode,
        admin_level: payload.adminLevel,
        allowed: payload.allowed,
        reason: "manual_request",
    });
    return response.data;
}

export type RbacApprovalRequestItem = {
    request_id: string;
    resource_key: string;
    role_code: string;
    admin_level: string;
    allowed: boolean;
    status: string;
    requested_by: string;
    reason?: string;
    applied_at?: string;
    created_at: string;
};

export async function listRbacApprovalRequests(status?: string): Promise<RbacApprovalRequestItem[]> {
    const response = await httpClient.get<{ items: RbacApprovalRequestItem[] }>("/v1/admin/rbac/approval-requests", {
        params: { status: status || undefined },
    });
    return response.data.items ?? [];
}

export async function approveRbacRequest(requestId: string, comment?: string) {
    const response = await httpClient.post(`/v1/admin/rbac/approval-requests/${requestId}/approve`, {
        comment: comment ?? "",
    });
    return response.data;
}

export async function rejectRbacRequest(requestId: string, comment?: string) {
    const response = await httpClient.post(`/v1/admin/rbac/approval-requests/${requestId}/reject`, {
        comment: comment ?? "",
    });
    return response.data;
}

export async function createAuditExportJob(payload: AuditExportJobCreateRequest): Promise<AuditExportJobCreateResponse> {
    const response = await httpClient.post<AuditExportJobCreateResponse>("/v1/admin/audit-logs/export-jobs", payload);
    return response.data;
}

export async function getAuditExportJob(jobId: string): Promise<AuditExportJobStatusResponse> {
    const response = await httpClient.get<AuditExportJobStatusResponse>(`/v1/admin/audit-logs/export-jobs/${jobId}`);
    return response.data;
}

export async function downloadAuditExportJob(jobId: string): Promise<Blob> {
    const response = await httpClient.get<Blob>(`/v1/admin/audit-logs/export-jobs/${jobId}/download`, {
        responseType: "blob",
    });
    return response.data;
}

export async function upsertBlock(blockValue: string, payload: { blockType: string; status?: string; reason?: string }) {
    const response = await httpClient.put(`/v1/ops/blocks/${encodeURIComponent(blockValue)}`, {
        block_type: payload.blockType,
        block_value: blockValue,
        status: payload.status ?? "ACTIVE",
        reason: payload.reason ?? "manual_block",
    });
    return response.data;
}
