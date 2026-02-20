package com.aichatbot.rag.presentation;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import java.util.Map;

public record RagAnswerRequest(
    @NotBlank String query,
    @JsonProperty("top_k") @Positive Integer topK,
    Map<String, String> filters,
    @JsonProperty("answer_contract") @Valid AnswerContractRequest answerContract
) {
    public record AnswerContractRequest(
        @JsonProperty("schema_version") String schemaVersion,
        @JsonProperty("citation_required") Boolean citationRequired,
        @JsonProperty("fail_closed") Boolean failClosed
    ) {
    }
}
