package com.aichatbot.rag.application;

import java.util.List;
import org.springframework.stereotype.Component;

@Component
public class NoopReranker {

    public List<RrfFusion.ScoredChunk> rerank(String queryMasked, List<RrfFusion.ScoredChunk> candidates) {
        return candidates;
    }
}
