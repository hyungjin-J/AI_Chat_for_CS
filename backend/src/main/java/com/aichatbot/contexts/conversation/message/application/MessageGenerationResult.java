package com.aichatbot.contexts.conversation.message.application;

public record MessageGenerationResult(
    String questionMessageId,
    String answerMessageId,
    boolean safeResponse,
    String errorCode
) {
}

