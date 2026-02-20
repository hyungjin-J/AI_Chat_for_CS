import type { SseMessage } from "../types/sse";

export class SseParser {
    private buffer = "";
    private eventName = "message";
    private eventId: string | undefined;
    private dataLines: string[] = [];

    feed(chunk: string): SseMessage[] {
        this.buffer += chunk;
        const lines = this.buffer.split(/\r?\n/);
        const endedWithNewline = /\r?\n$/.test(this.buffer);
        this.buffer = endedWithNewline ? "" : (lines.pop() ?? "");

        const messages: SseMessage[] = [];
        for (const line of lines) {
            const flushed = this.processLine(line);
            if (flushed) {
                messages.push(flushed);
            }
        }
        return messages;
    }

    flush(): SseMessage | null {
        if (this.buffer.length > 0) {
            // Why: 네트워크 청크가 빈 줄 없이 끝나도 마지막 이벤트를 복구하기 위해 flush 시 버퍼를 먼저 해석한다.
            const pendingLines = this.buffer.split(/\r?\n/);
            this.buffer = "";
            let flushedFromBuffer: SseMessage | null = null;
            for (const line of pendingLines) {
                const flushed = this.processLine(line);
                if (flushed) {
                    flushedFromBuffer = flushed;
                }
            }
            if (flushedFromBuffer) {
                return flushedFromBuffer;
            }
        }

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

    private processLine(line: string): SseMessage | null {
        if (line === "") {
            return this.flushCurrentEvent();
        }

        if (line.startsWith("event:")) {
            this.eventName = line.slice(6).trim();
            return null;
        }
        if (line.startsWith("id:")) {
            this.eventId = line.slice(3).trim();
            return null;
        }
        if (line.startsWith("data:")) {
            this.dataLines.push(line.slice(5).trimStart());
            return null;
        }
        return null;
    }

    private flushCurrentEvent(): SseMessage | null {
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
