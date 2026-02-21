import { useEffect, useState } from "react";
import { fetchDashboardSeries, fetchDashboardSummary } from "../api/adminApi";
import { getAuthState } from "../auth/authStore";

type DashboardData = {
    summary: Record<string, number>;
    series: Array<{ hour: string; metric: string; value: number }>;
};

export function AdminDashboardPage() {
    const [fromUtc, setFromUtc] = useState("");
    const [toUtc, setToUtc] = useState("");
    const [data, setData] = useState<DashboardData>({ summary: {}, series: [] });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        setError("");
        try {
            const tenantId = undefined;
            const summary = await fetchDashboardSummary({ tenantId, fromUtc: fromUtc || undefined, toUtc: toUtc || undefined });
            const series = await fetchDashboardSeries({ tenantId, fromUtc: fromUtc || undefined, toUtc: toUtc || undefined });
            setData({
                summary: summary.totals ?? {},
                series: (series.series ?? []).map((row) => ({
                    hour: row.hour_bucket_utc,
                    metric: row.metric_key,
                    value: row.metric_value,
                })),
            });
        } catch (caught) {
            const message = typeof caught === "object" && caught !== null && "message" in caught
                ? String((caught as { message?: string }).message ?? "Failed to load dashboard")
                : "Failed to load dashboard";
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void load();
    }, []);

    return (
        <section>
            <h2>OPS Dashboard</h2>
            <p>UTC metrics for tenant: {getAuthState().tenantKey}</p>
            <div className="toolbar">
                <label>
                    From UTC
                    <input
                        placeholder="2026-02-21T00:00:00Z"
                        value={fromUtc}
                        onChange={(event) => setFromUtc(event.target.value)}
                    />
                </label>
                <label>
                    To UTC
                    <input
                        placeholder="2026-02-21T23:59:59Z"
                        value={toUtc}
                        onChange={(event) => setToUtc(event.target.value)}
                    />
                </label>
                <button onClick={() => void load()} disabled={loading}>
                    Reload
                </button>
            </div>
            {error && <p className="error">{error}</p>}

            <h3>Summary</h3>
            <div className="card-grid">
                {Object.entries(data.summary).map(([metric, value]) => (
                    <article key={metric} className="metric-card">
                        <strong>{metric}</strong>
                        <span>{value}</span>
                    </article>
                ))}
                {Object.keys(data.summary).length === 0 && <p>No summary data.</p>}
            </div>

            <h3>Series</h3>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Hour (UTC)</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {data.series.map((row, index) => (
                        <tr key={`${row.hour}-${row.metric}-${index}`}>
                            <td>{row.hour}</td>
                            <td>{row.metric}</td>
                            <td>{row.value}</td>
                        </tr>
                    ))}
                    {data.series.length === 0 && (
                        <tr>
                            <td colSpan={3}>No series data.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </section>
    );
}

