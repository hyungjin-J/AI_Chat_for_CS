package com.aichatbot.message.application;

public record StreamEventView(
    int eventSeq,
    String eventType,
    String payloadJson
) {
}
