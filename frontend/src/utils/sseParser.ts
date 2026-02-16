import type { SseMessage } from "../types/sse";

export class SseParser {
    private buffer = "";
    private eventName = "message";
    private eventId: string | undefined;
    private dataLines: string[] = [];

    feed(chunk: string): SseMessage[] {
        this.buffer += chunk;
        const lines = this.buffer.split(/\r?\n/);
        this.buffer = lines.pop() ?? "";

        const messages: SseMessage[] = [];
        for (const line of lines) {
            if (line === "") {
                const flushed = this.flush();
                if (flushed) {
                    messages.push(flushed);
                }
                continue;
            }

            if (line.startsWith("event:")) {
                this.eventName = line.slice(6).trim();
                continue;
            }
            if (line.startsWith("id:")) {
                this.eventId = line.slice(3).trim();
                continue;
            }
            if (line.startsWith("data:")) {
                this.dataLines.push(line.slice(5).trimStart());
            }
        }
        return messages;
    }

    flush(): SseMessage | null {
        if (this.dataLines.length === 0) {
            this.eventName = "message";
            this.eventId = undefined;
            return null;
        }

        const payload: SseMessage = {
            id: this.eventId,
            event: this.eventName as SseMessage["event"],
            data: this.dataLines.join("\n"),
        };

        this.eventName = "message";
        this.eventId = undefined;
        this.dataLines = [];
        return payload;
    }
}
