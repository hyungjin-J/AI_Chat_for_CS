package com.aichatbot.contexts.knowledge.rag.application;

import com.aichatbot.contexts.knowledge.rag.presentation.RagAuxiliaryResponse;
import com.aichatbot.contexts.knowledge.rag.presentation.RagClarifySuggestRequest;
import com.aichatbot.contexts.knowledge.rag.presentation.RagQueryClassifyRequest;
import com.aichatbot.platform.observability.TraceGuard;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class RagAuxiliaryService {

    public RagAuxiliaryResponse classify(UUID tenantId, RagQueryClassifyRequest request) {
        String lowered = request.query().toLowerCase(Locale.ROOT);
        String intent = lowered.contains("refund") || lowered.contains("return") ? "refund_policy" : "general_inquiry";
        List<String> suggestions = "refund_policy".equals(intent)
            ? List.of("refund timeline", "required evidence", "processing channel")
            : List.of("clarify account context", "clarify order id", "clarify desired outcome");
        return new RagAuxiliaryResponse("ok", intent, suggestions, TraceGuard.requireTraceId());
    }

    public RagAuxiliaryResponse suggestClarify(UUID tenantId, RagClarifySuggestRequest request) {
        return new RagAuxiliaryResponse(
            "ok",
            "clarify",
            List.of(
                "Please share the order status and payment channel.",
                "Please confirm whether the delivery is delayed or damaged."
            ),
            TraceGuard.requireTraceId()
        );
    }
}
