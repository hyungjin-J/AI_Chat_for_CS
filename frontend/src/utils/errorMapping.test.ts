import { toUserError } from "./errorMapping";

describe("toUserError", () => {
    it("maps 400/422 to format error message", () => {
        expect(toUserError(400, { error_code: "API-003-422" }, "x")).toEqual({
            errorCode: "API-003-422",
            message: "Request format is invalid. Please verify session/message identifiers.",
        });
        expect(toUserError(422, null, "x").errorCode).toBe("API-003-422");
    });

    it("maps 403 to permission message", () => {
        expect(toUserError(403, { error_code: "SEC-002-403" }, "x")).toEqual({
            errorCode: "SEC-002-403",
            message: "You do not have permission to access this tenant resource.",
        });
    });

    it("maps 404 to not found message", () => {
        expect(toUserError(404, { error_code: "API-004-404" }, "Session does not exist.")).toEqual({
            errorCode: "API-004-404",
            message: "Session does not exist.",
        });
    });

    it("falls back to generic message for unknown status", () => {
        expect(toUserError(500, null, "x")).toEqual({
            errorCode: "SYS-003-500",
            message: "Request failed",
        });
    });
});
