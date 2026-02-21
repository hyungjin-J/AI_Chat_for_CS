import { useEffect, useState } from "react";
import type { AuditLogItem } from "../api/adminApi";
import { createAuditExportJob, downloadAuditExportJob, fetchAuditDiff, fetchAuditLogs, getAuditExportJob } from "../api/adminApi";

export function AdminAuditPage() {
    const [actionType, setActionType] = useState("");
    const [traceId, setTraceId] = useState("");
    const [fromUtc, setFromUtc] = useState("");
    const [toUtc, setToUtc] = useState("");
    const [items, setItems] = useState<AuditLogItem[]>([]);
    const [selectedDiff, setSelectedDiff] = useState<{ before: string; after: string } | null>(null);
    const [exportStatus, setExportStatus] = useState("");
    const [error, setError] = useState("");

    const load = async () => {
        setError("");
        try {
            const response = await fetchAuditLogs({
                fromUtc: fromUtc || undefined,
                toUtc: toUtc || undefined,
                actionType: actionType || undefined,
                traceId: traceId || undefined,
            });
            setItems(response.items ?? []);
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to load audit logs")
                : "Failed to load audit logs";
            setError(message);
        }
    };

    const onExport = async (format: "json" | "csv") => {
        try {
            setExportStatus("Export job requested...");
            const created = await createAuditExportJob({
                format,
                from_utc: fromUtc || undefined,
                to_utc: toUtc || undefined,
                row_limit: 1000,
            });
            let currentStatus = created.status;
            let attempts = 0;
            while ((currentStatus === "PENDING" || currentStatus === "RUNNING") && attempts < 20) {
                await new Promise((resolve) => setTimeout(resolve, 1500));
                const polled = await getAuditExportJob(created.job_id);
                currentStatus = polled.status;
                setExportStatus(`Export job status: ${currentStatus}`);
                if (currentStatus === "FAILED") {
                    throw new Error(polled.error_message ?? polled.error_code ?? "Export job failed");
                }
                if (currentStatus === "EXPIRED") {
                    throw new Error("Export job expired before download");
                }
                attempts += 1;
            }
            if (currentStatus !== "DONE") {
                throw new Error("Export job timeout. Please retry.");
            }

            const blob = await downloadAuditExportJob(created.job_id);
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `audit_export.${format}`;
            link.click();
            URL.revokeObjectURL(url);
            setExportStatus("Export download completed.");
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to export logs")
                : "Failed to export logs";
            setError(message);
            setExportStatus("");
        }
    };

    const loadDiff = async (auditId: string) => {
        try {
            const diff = await fetchAuditDiff(auditId);
            setSelectedDiff({
                before: diff.before_json ?? "{}",
                after: diff.after_json ?? "{}",
            });
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to load audit diff")
                : "Failed to load audit diff";
            setError(message);
        }
    };

    useEffect(() => {
        void load();
    }, []);

    return (
        <section>
            <h2>Audit Logs</h2>
            <div className="toolbar">
                <label>
                    Action Type
                    <input value={actionType} onChange={(event) => setActionType(event.target.value)} />
                </label>
                <label>
                    Trace ID
                    <input value={traceId} onChange={(event) => setTraceId(event.target.value)} />
                </label>
                <label>
                    From UTC
                    <input value={fromUtc} onChange={(event) => setFromUtc(event.target.value)} placeholder="2026-03-01T00:00:00Z" />
                </label>
                <label>
                    To UTC
                    <input value={toUtc} onChange={(event) => setToUtc(event.target.value)} placeholder="2026-03-31T23:59:59Z" />
                </label>
                <button onClick={() => void load()}>Search</button>
                <button onClick={() => void onExport("json")}>Export JSON</button>
                <button onClick={() => void onExport("csv")}>Export CSV</button>
            </div>
            {error && <p className="error">{error}</p>}
            {exportStatus && <p>{exportStatus}</p>}
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Action</th>
                        <th>Actor</th>
                        <th>Trace</th>
                        <th>Created</th>
                        <th>Diff</th>
                    </tr>
                </thead>
                <tbody>
                    {items.map((item) => (
                        <tr key={item.audit_id}>
                            <td>{item.action_type}</td>
                            <td>{item.actor_user_id ?? "-"}</td>
                            <td>{item.trace_id}</td>
                            <td>{item.created_at}</td>
                            <td>
                                <button onClick={() => void loadDiff(item.audit_id)}>View</button>
                            </td>
                        </tr>
                    ))}
                    {items.length === 0 && (
                        <tr>
                            <td colSpan={5}>No audit logs.</td>
                        </tr>
                    )}
                </tbody>
            </table>

            {selectedDiff && (
                <div className="diff-grid">
                    <article>
                        <h3>Before</h3>
                        <pre>{selectedDiff.before}</pre>
                    </article>
                    <article>
                        <h3>After</h3>
                        <pre>{selectedDiff.after}</pre>
                    </article>
                </div>
            )}
        </section>
    );
}
