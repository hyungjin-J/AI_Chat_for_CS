export type ErrorBanner = {
    errorCode: string;
    message: string;
};

export type ApiErrorPayload = {
    error_code?: string;
    message?: string;
};

export function toUserError(status: number, payload: ApiErrorPayload | null, notFoundMessage: string): ErrorBanner {
    if (status === 400 || status === 422) {
        return {
            errorCode: payload?.error_code ?? "API-003-422",
            message: "Request format is invalid. Please verify session/message identifiers.",
        };
    }

    if (status === 403) {
        return {
            errorCode: payload?.error_code ?? "SEC-002-403",
            message: "You do not have permission to access this tenant resource.",
        };
    }

    if (status === 404) {
        return {
            errorCode: payload?.error_code ?? "API-004-404",
            message: notFoundMessage,
        };
    }

    return {
        errorCode: payload?.error_code ?? "SYS-003-500",
        message: payload?.message ?? "Request failed",
    };
}
