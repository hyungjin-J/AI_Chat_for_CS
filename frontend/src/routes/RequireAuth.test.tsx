import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { clearAuthState, setAuthState } from "../auth/authStore";
import { RequireAuth } from "./RequireAuth";

function renderWithRoutes(path: string) {
    return render(
        <MemoryRouter initialEntries={[path]}>
            <Routes>
                <Route path="/login" element={<p>login-page</p>} />
                <Route path="/forbidden" element={<p>forbidden-page</p>} />
                <Route element={<RequireAuth roles={["OPS"]} />}>
                    <Route path="/admin/dashboard" element={<p>dashboard-page</p>} />
                </Route>
            </Routes>
        </MemoryRouter>,
    );
}

describe("RequireAuth", () => {
    beforeEach(() => {
        clearAuthState();
    });

    it("redirects to login when no access token exists", () => {
        renderWithRoutes("/admin/dashboard");
        expect(screen.getByText("login-page")).toBeInTheDocument();
    });

    it("redirects to forbidden when role is missing", () => {
        setAuthState({
            tenantKey: "demo-tenant",
            accessToken: "access",
            roles: ["AGENT"],
        });
        renderWithRoutes("/admin/dashboard");
        expect(screen.getByText("forbidden-page")).toBeInTheDocument();
    });

    it("renders protected route when role matches", () => {
        setAuthState({
            tenantKey: "demo-tenant",
            accessToken: "access",
            roles: ["OPS"],
        });
        renderWithRoutes("/admin/dashboard");
        expect(screen.getByText("dashboard-page")).toBeInTheDocument();
    });
});

