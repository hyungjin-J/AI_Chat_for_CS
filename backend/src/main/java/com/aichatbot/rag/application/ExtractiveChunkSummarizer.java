package com.aichatbot.rag.application;

import com.aichatbot.global.privacy.PiiMaskingService;
import org.springframework.stereotype.Component;

@Component
public class ExtractiveChunkSummarizer {

    private final PiiMaskingService piiMaskingService;

    public ExtractiveChunkSummarizer(PiiMaskingService piiMaskingService) {
        this.piiMaskingService = piiMaskingService;
    }

    public String summarize(String rawChunkText, int maxSentences) {
        String masked = piiMaskingService.mask(rawChunkText == null ? "" : rawChunkText.trim());
        if (masked.isBlank()) {
            return "";
        }
        int safeMaxSentences = Math.max(1, maxSentences);
        String[] sentences = masked.split("(?<=[.!?])\\s+");
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < Math.min(safeMaxSentences, sentences.length); i++) {
            if (i > 0) {
                builder.append(' ');
            }
            builder.append(sentences[i].trim());
        }
        return builder.toString().trim();
    }
}
