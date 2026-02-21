import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getAuthState, hasAnyRole } from "../auth/authStore";
import { logout } from "../api/authApi";

export function AdminShell() {
    const navigate = useNavigate();
    const auth = getAuthState();
    const showRbac = hasAnyRole("ADMIN");

    const onLogout = async () => {
        await logout();
        navigate("/login", { replace: true });
    };

    return (
        <div className="console-shell">
            <header className="console-header">
                <h1>Ops/Admin Console</h1>
                <div className="console-meta">
                    <span>Tenant: {auth.tenantKey}</span>
                    <span>Roles: {auth.roles.join(", ") || "-"}</span>
                    <button onClick={onLogout}>Logout</button>
                </div>
            </header>
            <div className="console-body">
                <aside className="console-sidebar">
                    <NavLink to="/admin/dashboard">Dashboard</NavLink>
                    <NavLink to="/admin/audit">Audit Logs</NavLink>
                    <NavLink to="/admin/blocks">Blocks</NavLink>
                    <NavLink to="/admin/sessions">Sessions</NavLink>
                    {showRbac && <NavLink to="/admin/rbac">RBAC Matrix</NavLink>}
                </aside>
                <section className="console-content">
                    <Outlet />
                </section>
            </div>
        </div>
    );
}
