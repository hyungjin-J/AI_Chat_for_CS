package com.aichatbot.message.application;

public record BudgetSnapshot(
    int inputTokens,
    int outputTokens,
    int toolCalls
) {
}
