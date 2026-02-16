export type SseEventType =
    | "token"
    | "tool"
    | "citation"
    | "done"
    | "error"
    | "safe_response"
    | "heartbeat";

export interface SseMessage {
    id?: string;
    event: SseEventType;
    data: string;
}
