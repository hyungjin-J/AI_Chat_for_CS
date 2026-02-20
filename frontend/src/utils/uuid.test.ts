import { isValidUuid } from "./uuid";

describe("isValidUuid", () => {
    it("returns true for RFC4122-like UUID values", () => {
        expect(isValidUuid("123e4567-e89b-12d3-a456-426614174000")).toBe(true);
        expect(isValidUuid("123E4567-E89B-42D3-A456-426614174000")).toBe(true);
    });

    it("returns false for invalid values", () => {
        expect(isValidUuid("abc")).toBe(false);
        expect(isValidUuid("123e4567-e89b-12d3-a456-42661417400")).toBe(false);
        expect(isValidUuid("  ")).toBe(false);
    });
});
