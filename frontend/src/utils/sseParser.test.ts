import { SseParser } from "./sseParser";

describe("SseParser", () => {
    it("parses token/citation/safe_response/error/done sequence", () => {
        const parser = new SseParser();
        const firstChunk = [
            "id:1",
            "event:token",
            "data:{\"text\":\"안\"}",
            "",
            "id:2",
            "event:citation",
            "data:{\"chunk_id\":\"c1\"}",
            "",
            "id:3",
            "event:safe_response",
            "data:{\"message\":\"safe\"}",
            "",
        ].join("\n");

        const secondChunk = [
            "id:4",
            "event:error",
            "data:{\"error_code\":\"AI-009-422-SCHEMA\"}",
            "",
            "id:5",
            "event:done",
            "data:{\"message_id\":\"m1\"}",
            "",
        ].join("\n");

        const events = [...parser.feed(firstChunk), ...parser.feed(secondChunk)];
        expect(events).toHaveLength(5);
        expect(events.map((event) => event.event)).toEqual([
            "token",
            "citation",
            "safe_response",
            "error",
            "done",
        ]);
        expect(events[0].id).toBe("1");
        expect(events[4].id).toBe("5");
    });

    it("flushes trailing event payload", () => {
        const parser = new SseParser();
        parser.feed("id:9\nevent:done\ndata:{\"ok\":true}");
        const tail = parser.flush();
        expect(tail).not.toBeNull();
        expect(tail?.event).toBe("done");
        expect(tail?.id).toBe("9");
    });
});
