package com.aichatbot.rag.presentation;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import java.util.Map;

public record RagRetrieveRequest(
    @NotBlank String query,
    @JsonProperty("top_k") @Positive Integer topK,
    Map<String, String> filters
) {
}
