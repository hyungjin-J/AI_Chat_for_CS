import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import App from "./App";

describe("App invalid session id guard", () => {
    it("shows an error and blocks API calls when URL session_id is invalid", async () => {
        const fetchMock = vi.fn();
        vi.stubGlobal("fetch", fetchMock);
        window.history.pushState({}, "", "/?session_id=abc");

        render(<App />);

        expect(await screen.findByText("API-003-422: Session ID format is invalid.")).toBeInTheDocument();
        expect(screen.getByText("Status: Invalid session id")).toBeInTheDocument();
        expect(fetchMock).not.toHaveBeenCalled();

        vi.unstubAllGlobals();
    });
});
