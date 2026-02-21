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

export async function exportAuditLogs(format: "json" | "csv"): Promise<string> {
    const response = await httpClient.get<string>("/v1/admin/audit-logs/export", {
        params: { format },
        responseType: "text",
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
