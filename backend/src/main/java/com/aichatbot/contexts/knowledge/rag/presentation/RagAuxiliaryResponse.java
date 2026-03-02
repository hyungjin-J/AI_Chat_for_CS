package com.aichatbot.contexts.knowledge.rag.presentation;

import java.util.List;

public record RagAuxiliaryResponse(
    String result,
    String intent,
    List<String> suggestions,
    String traceId
) {
}
