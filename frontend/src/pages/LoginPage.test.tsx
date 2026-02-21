import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { clearAuthState, setAuthState } from "../auth/authStore";
import { LoginPage } from "./LoginPage";

vi.mock("../api/authApi", () => ({
    login: vi.fn(async () => {
        setAuthState({
            tenantKey: "demo-tenant",
            accessToken: "token",
            sessionFamilyId: "family-1",
            roles: ["OPS"],
            adminLevel: "MANAGER",
            permissionVersion: 1,
        });
        return { status: "accepted" as const };
    }),
}));

describe("LoginPage", () => {
    beforeEach(() => {
        clearAuthState();
    });

    it("submits login and navigates to dashboard for OPS role", async () => {
        const user = userEvent.setup();
        render(
            <MemoryRouter initialEntries={["/login"]}>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/admin/dashboard" element={<p>dashboard-page</p>} />
                    <Route path="/forbidden" element={<p>forbidden-page</p>} />
                </Routes>
            </MemoryRouter>,
        );

        await user.click(screen.getByRole("button", { name: "Login" }));
        expect(await screen.findByText("dashboard-page")).toBeInTheDocument();
    });
});
