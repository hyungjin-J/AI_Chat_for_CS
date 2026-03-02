package com.aichatbot.contexts.knowledge.rag.application;

import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class DefaultKbDocumentParser implements KbDocumentParser {

    private static final int MAX_CHUNK_CHARS = 480;

    @Override
    public List<String> parseMaskedContent(String rawContentMasked) {
        String normalized = normalize(rawContentMasked);
        if (normalized.isBlank()) {
            throw new KbIndexingStageException("KB-INDEX-PARSER-422", "parser returned empty content", true);
        }

        String[] paragraphCandidates = normalized.split("\\n{2,}");
        List<String> chunks = new ArrayList<>();
        for (String paragraph : paragraphCandidates) {
            String trimmed = paragraph.trim();
            if (trimmed.isBlank()) {
                continue;
            }
            if (trimmed.length() <= MAX_CHUNK_CHARS) {
                chunks.add(trimmed);
                continue;
            }
            for (int start = 0; start < trimmed.length(); start += MAX_CHUNK_CHARS) {
                int end = Math.min(trimmed.length(), start + MAX_CHUNK_CHARS);
                String slice = trimmed.substring(start, end).trim();
                if (!slice.isBlank()) {
                    chunks.add(slice);
                }
            }
        }

        if (chunks.isEmpty()) {
            throw new KbIndexingStageException("KB-INDEX-PARSER-422", "parser returned no chunks", true);
        }
        return chunks;
    }

    private String normalize(String rawValue) {
        if (rawValue == null) {
            return "";
        }
        return rawValue
            .replace("\r\n", "\n")
            .replace('\r', '\n')
            .replaceAll("[\\t ]+", " ")
            .replaceAll("\n{3,}", "\n\n")
            .trim();
    }
}
