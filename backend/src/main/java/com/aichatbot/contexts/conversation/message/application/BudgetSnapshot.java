package com.aichatbot.contexts.conversation.message.application;

public record BudgetSnapshot(
    int inputTokens,
    int outputTokens,
    int toolCalls
) {
}

