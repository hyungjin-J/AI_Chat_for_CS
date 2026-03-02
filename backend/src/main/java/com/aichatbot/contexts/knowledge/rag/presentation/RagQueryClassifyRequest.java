package com.aichatbot.contexts.knowledge.rag.presentation;

import jakarta.validation.constraints.NotBlank;

public record RagQueryClassifyRequest(
    @NotBlank
    String query
) {
}
