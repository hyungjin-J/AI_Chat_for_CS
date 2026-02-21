import { useEffect, useState } from "react";
import { fetchMySessions, revokeOtherSessions, revokeSession, type SessionItem } from "../api/authApi";

export function AdminSessionsPage() {
    const [sessions, setSessions] = useState<SessionItem[]>([]);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        setError("");
        try {
            const rows = await fetchMySessions();
            setSessions(rows);
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to load sessions")
                : "Failed to load sessions";
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const onRevoke = async (sessionId: string) => {
        try {
            await revokeSession(sessionId);
            await load();
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to revoke session")
                : "Failed to revoke session";
            setError(message);
        }
    };

    const onRevokeOthers = async () => {
        try {
            await revokeOtherSessions();
            await load();
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to revoke other sessions")
                : "Failed to revoke other sessions";
            setError(message);
        }
    };

    useEffect(() => {
        void load();
    }, []);

    return (
        <section>
            <h2>My Sessions</h2>
            <div className="toolbar">
                <button onClick={() => void load()} disabled={loading}>Reload</button>
                <button onClick={() => void onRevokeOthers()}>Revoke Other Sessions</button>
            </div>
            {error && <p className="error">{error}</p>}
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Session</th>
                        <th>Client</th>
                        <th>Created</th>
                        <th>Last Seen</th>
                        <th>Expires</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {sessions.map((session) => (
                        <tr key={session.session_id}>
                            <td>{session.session_id}</td>
                            <td>{session.client_type ?? "-"}</td>
                            <td>{session.created_at}</td>
                            <td>{session.last_seen_at}</td>
                            <td>{session.expires_at}</td>
                            <td>
                                <button onClick={() => void onRevoke(session.session_id)}>Revoke</button>
                            </td>
                        </tr>
                    ))}
                    {sessions.length === 0 && (
                        <tr>
                            <td colSpan={6}>No active sessions.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </section>
    );
}
