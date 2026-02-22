import axios from "axios";
import { clearAuthState, getAuthState, resetStale401Count, setAuthState } from "../auth/authStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export type LoginPayload = {
    tenantKey: string;
    loginId: string;
    password: string;
    clientType: string;
};

type AuthResponse = {
    result: string;
    access_token: string;
    refresh_token?: string;
    session_family_id?: string;
    mfa_ticket_id?: string;
    mfa_status?: string;
    roles: string[];
    admin_level?: string;
    permission_version?: number;
    recovery_codes?: string[];
    trace_id: string;
};

export type LoginResult =
    | { status: "accepted" }
    | { status: "mfa_required" | "mfa_setup_required"; mfaTicketId: string };

function traceId(): string {
    return crypto.randomUUID();
}

function idempotencyKey(): string {
    return crypto.randomUUID();
}

export async function login(payload: LoginPayload): Promise<LoginResult> {
    const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/v1/auth/login`,
        {
            login_id: payload.loginId,
            password: payload.password,
            client_type: payload.clientType,
            channel_id: "agent-console",
            client_nonce: crypto.randomUUID(),
        },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": payload.tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );

    if (response.data.result === "mfa_required" || response.data.result === "mfa_setup_required") {
        return {
            status: response.data.result,
            mfaTicketId: response.data.mfa_ticket_id ?? "",
        };
    }

    setAuthState({
        tenantKey: payload.tenantKey,
        accessToken: response.data.access_token,
        sessionFamilyId: response.data.session_family_id ?? "",
        roles: response.data.roles ?? [],
        adminLevel: response.data.admin_level ?? "",
        permissionVersion: response.data.permission_version ?? 0,
        stalePermission401Count: 0,
    });
    return { status: "accepted" };
}

export async function refreshToken(tenantKey: string): Promise<string> {
    const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/v1/auth/refresh`,
        {
            client_type: "web",
            client_nonce: crypto.randomUUID(),
        },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );
    setAuthState({
        accessToken: response.data.access_token,
        sessionFamilyId: response.data.session_family_id ?? "",
        roles: response.data.roles ?? [],
        adminLevel: response.data.admin_level ?? "",
        permissionVersion: response.data.permission_version ?? 0,
    });
    resetStale401Count();
    return response.data.access_token;
}

export async function logout(): Promise<void> {
    const tenantKey = getAuthState().tenantKey;
    try {
        await axios.post(
            `${API_BASE_URL}/v1/auth/logout`,
            {
                client_type: "web",
                client_nonce: crypto.randomUUID(),
                reason: "user_requested_logout",
            },
            {
                withCredentials: true,
                headers: {
                    "Content-Type": "application/json",
                    "X-Tenant-Key": tenantKey,
                    "X-Trace-Id": traceId(),
                    "Idempotency-Key": idempotencyKey(),
                },
            },
        );
    } finally {
        clearAuthState();
    }
}

export type MfaEnrollResponse = {
    result: string;
    mfa_ticket_id: string;
    totp_secret: string;
    otpauth_uri: string;
    trace_id: string;
};

export async function enrollMfaTotp(tenantKey: string, mfaTicketId: string): Promise<MfaEnrollResponse> {
    const response = await axios.post<MfaEnrollResponse>(
        `${API_BASE_URL}/v1/auth/mfa/totp/enroll`,
        { mfa_ticket_id: mfaTicketId },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );
    return response.data;
}

export async function activateMfaTotp(tenantKey: string, mfaTicketId: string, totpCode: string): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/v1/auth/mfa/totp/activate`,
        { mfa_ticket_id: mfaTicketId, totp_code: totpCode, client_type: "web" },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );
    setAuthState({
        tenantKey,
        accessToken: response.data.access_token,
        sessionFamilyId: response.data.session_family_id ?? "",
        roles: response.data.roles ?? [],
        adminLevel: response.data.admin_level ?? "",
        permissionVersion: response.data.permission_version ?? 0,
    });
    return response.data;
}

export async function verifyMfa(
    tenantKey: string,
    mfaTicketId: string,
    totpCode: string,
    recoveryCode?: string,
): Promise<AuthResponse> {
    const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/v1/auth/mfa/verify`,
        {
            mfa_ticket_id: mfaTicketId,
            totp_code: totpCode || undefined,
            recovery_code: recoveryCode || undefined,
            client_type: "web",
        },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );
    setAuthState({
        tenantKey,
        accessToken: response.data.access_token,
        sessionFamilyId: response.data.session_family_id ?? "",
        roles: response.data.roles ?? [],
        adminLevel: response.data.admin_level ?? "",
        permissionVersion: response.data.permission_version ?? 0,
    });
    return response.data;
}

export type SessionItem = {
    session_id: string;
    created_at: string;
    last_seen_at: string;
    expires_at: string;
    client_type?: string;
    device_name?: string;
    created_ip?: string;
    consumed_ip?: string;
};

export async function fetchMySessions(): Promise<SessionItem[]> {
    const { tenantKey } = getAuthState();
    const response = await axios.get<{ items: SessionItem[] }>(
        `${API_BASE_URL}/v1/auth/sessions`,
        {
            withCredentials: true,
            headers: {
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
            },
        },
    );
    return response.data.items ?? [];
}

export async function revokeSession(sessionId: string): Promise<void> {
    const { tenantKey, sessionFamilyId } = getAuthState();
    await axios.delete(`${API_BASE_URL}/v1/auth/sessions/${sessionId}`, {
        withCredentials: true,
        params: {
            current_session_id: sessionFamilyId || undefined,
        },
        headers: {
            "X-Tenant-Key": tenantKey,
            "X-Trace-Id": traceId(),
            "Idempotency-Key": idempotencyKey(),
        },
    });
}

export async function revokeOtherSessions(): Promise<void> {
    const { tenantKey, sessionFamilyId } = getAuthState();
    await axios.post(
        `${API_BASE_URL}/v1/auth/sessions/revoke-others`,
        { current_session_id: sessionFamilyId },
        {
            withCredentials: true,
            headers: {
                "Content-Type": "application/json",
                "X-Tenant-Key": tenantKey,
                "X-Trace-Id": traceId(),
                "Idempotency-Key": idempotencyKey(),
            },
        },
    );
}
