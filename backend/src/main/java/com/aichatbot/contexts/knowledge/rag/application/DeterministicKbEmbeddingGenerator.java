package com.aichatbot.contexts.knowledge.rag.application;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.stereotype.Component;

@Component
public class DeterministicKbEmbeddingGenerator implements KbEmbeddingGenerator {

    @Override
    public String generateEmbeddingVector(String embeddingInputText) {
        String normalized = embeddingInputText == null ? "" : embeddingInputText.trim();
        if (normalized.isBlank()) {
            throw new KbIndexingStageException("KB-INDEX-EMBED-422", "embedding input was blank", false);
        }

        byte[] digest;
        try {
            digest = MessageDigest.getInstance("SHA-256")
                .digest(normalized.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exception) {
            throw new KbIndexingStageException("KB-INDEX-EMBED-500", "embedding digest failed", false, exception);
        }

        double first = toUnit(digest[0], digest[1], digest[2], digest[3]);
        double second = toUnit(digest[4], digest[5], digest[6], digest[7]);
        double third = toUnit(digest[8], digest[9], digest[10], digest[11]);
        return String.format("[%.6f,%.6f,%.6f]", first, second, third);
    }

    private double toUnit(byte b1, byte b2, byte b3, byte b4) {
        long raw = ((long) (b1 & 0xFF) << 24)
            | ((long) (b2 & 0xFF) << 16)
            | ((long) (b3 & 0xFF) << 8)
            | (b4 & 0xFFL);
        return (raw % 1_000_000L) / 1_000_000.0d;
    }
}
