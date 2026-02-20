package com.aichatbot.rag.application;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Component;

@Component
public class RrfFusion {

    public List<ScoredChunk> fuse(List<ScoredChunk> vectorRanked, List<ScoredChunk> bm25Ranked, int rrfK) {
        Map<UUID, MutableScore> scores = new HashMap<>();
        apply(scores, vectorRanked, rrfK);
        apply(scores, bm25Ranked, rrfK);

        List<ScoredChunk> fused = new ArrayList<>();
        for (Map.Entry<UUID, MutableScore> entry : scores.entrySet()) {
            MutableScore value = entry.getValue();
            fused.add(new ScoredChunk(entry.getKey(), value.score, value.previewText));
        }
        fused.sort(Comparator.comparing(ScoredChunk::score).reversed().thenComparing(c -> c.chunkId().toString()));
        return fused;
    }

    private void apply(Map<UUID, MutableScore> scores, List<ScoredChunk> ranked, int rrfK) {
        for (int i = 0; i < ranked.size(); i++) {
            ScoredChunk row = ranked.get(i);
            int rank = i + 1;
            double delta = 1.0d / (rrfK + rank);
            scores.computeIfAbsent(row.chunkId(), ignored -> new MutableScore(row.previewText())).add(delta);
        }
    }

    private static final class MutableScore {
        private double score;
        private final String previewText;

        private MutableScore(String previewText) {
            this.previewText = previewText;
        }

        private void add(double delta) {
            score += delta;
        }
    }

    public record ScoredChunk(UUID chunkId, double score, String previewText) {
    }
}
