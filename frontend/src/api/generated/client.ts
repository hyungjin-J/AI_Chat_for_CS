import createClient from "openapi-fetch";
import type { paths } from "./openapi";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export function makeTraceId(): string {
    return crypto.randomUUID();
}

export function makeIdempotencyKey(): string {
    return crypto.randomUUID();
}

type HeaderInput = {
    tenantKey?: string;
    accessToken?: string;
    includeIdempotencyKey?: boolean;
    traceId?: string;
    extra?: Record<string, string>;
};

export function buildGeneratedHeaders(input: HeaderInput): Record<string, string> {
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-Trace-Id": input.traceId ?? makeTraceId(),
    };
    if (input.tenantKey) {
        headers["X-Tenant-Key"] = input.tenantKey;
    }
    if (input.accessToken) {
        headers.Authorization = `Bearer ${input.accessToken}`;
    }
    if (input.includeIdempotencyKey) {
        headers["Idempotency-Key"] = makeIdempotencyKey();
    }
    if (input.extra) {
        for (const [key, value] of Object.entries(input.extra)) {
            headers[key] = value;
        }
    }
    return headers;
}

export const generatedApiClient = createClient<paths>({
    baseUrl: API_BASE_URL,
    fetch: (request: Request) => {
        const requestWithCredentials = new Request(request, {
            credentials: "include",
        });
        return fetch(requestWithCredentials);
    },
});
