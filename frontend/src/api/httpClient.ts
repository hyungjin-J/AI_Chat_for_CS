import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import {
    clearAuthState,
    getAuthState,
    incrementStale401Count,
    resetStale401Count,
    setAuthState,
} from "../auth/authStore";
import { refreshToken } from "./authApi";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

type RetriableRequestConfig = InternalAxiosRequestConfig & {
    _retryAuth?: boolean;
};

export const httpClient = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

let refreshInFlight: Promise<string> | null = null;

function forceLoginRedirect() {
    clearAuthState();
    if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
    }
}

httpClient.interceptors.request.use((config) => {
    const auth = getAuthState();
    const nextConfig = config;
    nextConfig.headers.set("X-Trace-Id", crypto.randomUUID());
    if (auth.tenantKey) {
        nextConfig.headers.set("X-Tenant-Key", auth.tenantKey);
    }
    if (auth.accessToken) {
        nextConfig.headers.set("Authorization", `Bearer ${auth.accessToken}`);
    }
    if (!nextConfig.headers.has("Idempotency-Key") && nextConfig.method?.toUpperCase() === "POST") {
        nextConfig.headers.set("Idempotency-Key", crypto.randomUUID());
    }
    return nextConfig;
});

httpClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const response = error.response;
        const originalRequest = error.config as RetriableRequestConfig | undefined;

        if (!response || response.status !== 401 || !originalRequest) {
            return Promise.reject(error);
        }

        const errorCode = (response.data as { error_code?: string } | undefined)?.error_code;
        if (errorCode === "AUTH_STALE_PERMISSION") {
            const staleCount = incrementStale401Count();
            if (staleCount >= 2) {
                forceLoginRedirect();
                return Promise.reject(error);
            }
        }

        if (originalRequest._retryAuth) {
            forceLoginRedirect();
            return Promise.reject(error);
        }
        originalRequest._retryAuth = true;

        const { tenantKey } = getAuthState();
        if (!tenantKey) {
            forceLoginRedirect();
            return Promise.reject(error);
        }

        try {
            if (!refreshInFlight) {
                refreshInFlight = refreshToken(tenantKey);
            }
            const nextAccessToken = await refreshInFlight;
            refreshInFlight = null;
            resetStale401Count();
            setAuthState({ accessToken: nextAccessToken });
            originalRequest.headers.set("Authorization", `Bearer ${nextAccessToken}`);
            return httpClient.request(originalRequest);
        } catch (refreshError) {
            refreshInFlight = null;
            forceLoginRedirect();
            return Promise.reject(refreshError);
        }
    },
);
