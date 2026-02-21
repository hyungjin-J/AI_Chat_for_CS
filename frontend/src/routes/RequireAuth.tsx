import { Navigate, Outlet } from "react-router-dom";
import { getAuthState } from "../auth/authStore";

type RequireAuthProps = {
    roles?: string[];
};

export function RequireAuth({ roles = [] }: RequireAuthProps) {
    const auth = getAuthState();
    if (!auth.accessToken) {
        return <Navigate to="/login" replace />;
    }

    if (roles.length > 0) {
        const granted = auth.roles.map((role) => role.toUpperCase());
        const matched = roles.some((role) => granted.includes(role.toUpperCase()));
        if (!matched) {
            return <Navigate to="/forbidden" replace />;
        }
    }

    return <Outlet />;
}

