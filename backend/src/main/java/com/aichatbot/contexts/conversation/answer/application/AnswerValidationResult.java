package com.aichatbot.contexts.conversation.answer.application;

public record AnswerValidationResult(
    boolean valid,
    String errorCode,
    AnswerContract contract
) {
}

