package com.aichatbot.answer.application;

public record AnswerValidationResult(
    boolean valid,
    String errorCode,
    AnswerContract contract
) {
}
