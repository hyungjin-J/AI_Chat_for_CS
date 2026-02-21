import { Navigate, Route, Routes } from "react-router-dom";
import { AdminShell } from "./layout/AdminShell";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminRbacPage } from "./pages/AdminRbacPage";
import { AdminSessionsPage } from "./pages/AdminSessionsPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { LoginPage } from "./pages/LoginPage";
import { OpsBlockPage } from "./pages/OpsBlockPage";
import { RequireAuth } from "./routes/RequireAuth";
import "./index.css";

function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/forbidden" element={<ForbiddenPage />} />

            <Route element={<RequireAuth roles={["OPS", "ADMIN"]} />}>
                <Route path="/admin" element={<AdminShell />}>
                    <Route index element={<Navigate to="/admin/dashboard" replace />} />
                    <Route path="dashboard" element={<AdminDashboardPage />} />
                    <Route path="audit" element={<AdminAuditPage />} />
                    <Route path="blocks" element={<OpsBlockPage />} />
                    <Route path="sessions" element={<AdminSessionsPage />} />
                    <Route path="rbac" element={<AdminRbacPage />} />
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
    );
}

export default App;
