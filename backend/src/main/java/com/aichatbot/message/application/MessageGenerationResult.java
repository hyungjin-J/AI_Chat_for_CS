package com.aichatbot.message.application;

public record MessageGenerationResult(
    String questionMessageId,
    String answerMessageId,
    boolean safeResponse,
    String errorCode
) {
}
