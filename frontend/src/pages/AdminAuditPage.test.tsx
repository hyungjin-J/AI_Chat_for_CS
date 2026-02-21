import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminAuditPage } from "./AdminAuditPage";

vi.mock("../api/adminApi", () => ({
    fetchAuditLogs: vi.fn(async () => ({ tenant_id: "demo-tenant", items: [], trace_id: "trace-1" })),
    fetchAuditDiff: vi.fn(async () => ({
        audit_id: "a1",
        before_json: "{}",
        after_json: "{}",
        source_trace_id: "trace-1",
        trace_id: "trace-1",
    })),
    createAuditExportJob: vi.fn(async () => ({
        job_id: "job-1",
        status: "DONE",
        expires_at: "2026-03-11T00:00:00Z",
        trace_id: "trace-2",
    })),
    getAuditExportJob: vi.fn(async () => ({
        job_id: "job-1",
        status: "DONE",
        format: "json",
        row_count: 0,
        total_bytes: 2,
        created_at: "2026-03-10T00:00:00Z",
        completed_at: "2026-03-10T00:00:01Z",
        expires_at: "2026-03-11T00:00:00Z",
        trace_id: "trace-2",
    })),
    downloadAuditExportJob: vi.fn(async () => new Blob(["[]"], { type: "application/json" })),
}));

import { createAuditExportJob, downloadAuditExportJob } from "../api/adminApi";

describe("AdminAuditPage", () => {
    const createObjectURL = vi.fn(() => "blob:mock");
    const revokeObjectURL = vi.fn();

    beforeEach(() => {
        Object.defineProperty(global.URL, "createObjectURL", {
            writable: true,
            value: createObjectURL,
        });
        Object.defineProperty(global.URL, "revokeObjectURL", {
            writable: true,
            value: revokeObjectURL,
        });
    });

    it("creates export job and downloads artifact", async () => {
        const user = userEvent.setup();
        render(<AdminAuditPage />);

        await user.click(await screen.findByRole("button", { name: "Export JSON" }));

        await waitFor(() => {
            expect(createAuditExportJob).toHaveBeenCalledTimes(1);
            expect(downloadAuditExportJob).toHaveBeenCalledTimes(1);
        });
    });
});
