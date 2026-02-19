package com.aichatbot.message.application;

public record StreamEventView(
    int eventSeq,
    String eventType,
    String payloadJson
) {
    public StreamEventView(Integer eventSeq, String eventType, String payloadJson) {
        this(eventSeq == null ? 0 : eventSeq, eventType, payloadJson);
    }
}
