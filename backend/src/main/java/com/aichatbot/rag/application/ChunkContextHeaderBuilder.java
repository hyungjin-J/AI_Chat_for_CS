package com.aichatbot.rag.application;

import com.aichatbot.rag.infrastructure.ChunkSearchRow;
import org.springframework.stereotype.Component;

@Component
public class ChunkContextHeaderBuilder {

    public String build(ChunkSearchRow row, int totalChunks) {
        String title = safe(row.title(), "unknown");
        String version = row.versionNo() == null ? "0" : row.versionNo().toString();
        String chunkNo = row.chunkNo() == null ? "0" : row.chunkNo().toString();
        String source = safe(row.sourceType(), "unknown");
        String category = safe(row.category(), "unknown");
        String effective = safe(row.effectiveDate(), "unknown");
        String owner = safe(row.owner(), "unknown");
        return "[DOC] " + title
            + " | ver=" + version
            + " | chunk=" + chunkNo + "/" + Math.max(1, totalChunks)
            + " | source=" + source
            + " | category=" + category
            + " | effective=" + effective
            + " | owner=" + owner
            + "\n[SECTION] " + title;
    }

    private String safe(String value, String fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value.trim();
    }
}
