package com.aichatbot.rag.application;

import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class EvidenceSelector {

    public List<RrfFusion.ScoredChunk> select(List<RrfFusion.ScoredChunk> fused, int topK, double threshold) {
        return fused.stream()
            .filter(item -> item.score() >= threshold)
            .limit(Math.max(1, topK))
            .toList();
    }
}
