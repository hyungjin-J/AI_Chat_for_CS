import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { approveRbacRequest, listRbacApprovalRequests, rejectRbacRequest, upsertRbacMatrix, type RbacApprovalRequestItem } from "../api/adminApi";

export function AdminRbacPage() {
    const [resourceKey, setResourceKey] = useState("admin.dashboard.summary");
    const [roleCode, setRoleCode] = useState("OPS");
    const [adminLevel, setAdminLevel] = useState("MANAGER");
    const [allowed, setAllowed] = useState(true);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");
    const [requests, setRequests] = useState<RbacApprovalRequestItem[]>([]);

    const onSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setMessage("");
        setError("");
        try {
            await upsertRbacMatrix(resourceKey, { roleCode, adminLevel, allowed });
            setMessage("RBAC change request created.");
            await loadRequests();
        } catch (caught) {
            const nextMessage = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Update failed")
                : "Update failed";
            setError(nextMessage);
        }
    };

    const loadRequests = async () => {
        try {
            const rows = await listRbacApprovalRequests("PENDING");
            setRequests(rows);
        } catch (caught) {
            const nextMessage = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to load requests")
                : "Failed to load requests";
            setError(nextMessage);
        }
    };

    const onApprove = async (requestId: string) => {
        setError("");
        try {
            await approveRbacRequest(requestId, "approve from console");
            await loadRequests();
        } catch (caught) {
            const nextMessage = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Approval failed")
                : "Approval failed";
            setError(nextMessage);
        }
    };

    const onReject = async (requestId: string) => {
        setError("");
        try {
            await rejectRbacRequest(requestId, "reject from console");
            await loadRequests();
        } catch (caught) {
            const nextMessage = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Reject failed")
                : "Reject failed";
            setError(nextMessage);
        }
    };

    useEffect(() => {
        void loadRequests();
    }, []);

    return (
        <section>
            <h2>RBAC Matrix</h2>
            <form className="inline-form" onSubmit={onSubmit}>
                <label>
                    Resource Key
                    <input value={resourceKey} onChange={(event) => setResourceKey(event.target.value)} />
                </label>
                <label>
                    Role Code
                    <input value={roleCode} onChange={(event) => setRoleCode(event.target.value)} />
                </label>
                <label>
                    Admin Level
                    <input value={adminLevel} onChange={(event) => setAdminLevel(event.target.value)} />
                </label>
                <label className="checkbox">
                    <input type="checkbox" checked={allowed} onChange={(event) => setAllowed(event.target.checked)} />
                    Allowed
                </label>
                <button type="submit">Apply</button>
            </form>
            {message && <p>{message}</p>}
            {error && <p className="error">{error}</p>}

            <h3>Pending Approval Requests</h3>
            <button onClick={() => void loadRequests()}>Reload Requests</button>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Request ID</th>
                        <th>Resource</th>
                        <th>Role</th>
                        <th>Admin Level</th>
                        <th>Allowed</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {requests.map((item) => (
                        <tr key={item.request_id}>
                            <td>{item.request_id}</td>
                            <td>{item.resource_key}</td>
                            <td>{item.role_code}</td>
                            <td>{item.admin_level}</td>
                            <td>{String(item.allowed)}</td>
                            <td>{item.status}</td>
                            <td>
                                <button onClick={() => void onApprove(item.request_id)}>Approve</button>
                                <button onClick={() => void onReject(item.request_id)}>Reject</button>
                            </td>
                        </tr>
                    ))}
                    {requests.length === 0 && (
                        <tr>
                            <td colSpan={7}>No pending requests.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </section>
    );
}
