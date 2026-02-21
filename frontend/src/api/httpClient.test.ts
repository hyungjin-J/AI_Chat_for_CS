import type { AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuthState, getAuthState, setAuthState } from "../auth/authStore";

vi.mock("./authApi", () => ({
    refreshToken: vi.fn(),
}));

import { refreshToken } from "./authApi";
import { httpClient } from "./httpClient";

function buildResponse(
    config: InternalAxiosRequestConfig,
    status: number,
    data: unknown,
): AxiosResponse {
    return {
        config,
        data,
        status,
        statusText: status === 200 ? "OK" : "Unauthorized",
        headers: {},
    };
}

function buildRejected401(config: InternalAxiosRequestConfig) {
    return Promise.reject({
        config,
        response: buildResponse(config, 401, { error_code: "AUTH_STALE_PERMISSION" }),
        isAxiosError: true,
    });
}

describe("httpClient interceptor", () => {
    beforeEach(() => {
        clearAuthState();
        setAuthState({
            tenantKey: "demo-tenant",
            accessToken: "old-access-token",
            roles: ["OPS"],
            stalePermission401Count: 0,
        });
        window.history.pushState({}, "", "/login");
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("retries once on 401 by using refresh token", async () => {
        vi.mocked(refreshToken).mockResolvedValue("new-access-token");
        const adapter = vi
            .fn<(config: InternalAxiosRequestConfig) => Promise<AxiosResponse>>()
            .mockImplementationOnce((config) => buildRejected401(config))
            .mockImplementationOnce(async (config) => buildResponse(config, 200, { ok: true }));

        httpClient.defaults.adapter = adapter as unknown as AxiosRequestConfig["adapter"];

        const response = await httpClient.get("/v1/admin/dashboard/summary");
        expect(response.data).toEqual({ ok: true });
        expect(vi.mocked(refreshToken)).toHaveBeenCalledTimes(1);
        expect(adapter).toHaveBeenCalledTimes(2);
        expect(getAuthState().accessToken).toBe("new-access-token");
    });

    it("forces login when stale permission repeats on retry", async () => {
        vi.mocked(refreshToken).mockResolvedValue("new-access-token");
        const adapter = vi
            .fn<(config: InternalAxiosRequestConfig) => Promise<AxiosResponse>>()
            .mockImplementationOnce((config) => buildRejected401(config))
            .mockImplementationOnce((config) => buildRejected401(config));

        httpClient.defaults.adapter = adapter as unknown as AxiosRequestConfig["adapter"];

        await expect(httpClient.get("/v1/admin/dashboard/summary")).rejects.toBeTruthy();
        expect(vi.mocked(refreshToken)).toHaveBeenCalledTimes(1);
        expect(getAuthState().accessToken).toBe("");
    });
});
