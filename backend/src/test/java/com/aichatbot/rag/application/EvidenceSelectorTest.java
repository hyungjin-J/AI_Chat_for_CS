package com.aichatbot.rag.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class EvidenceSelectorTest {

    private final EvidenceSelector evidenceSelector = new EvidenceSelector();

    @Test
    void shouldFilterOutBelowThreshold() {
        List<RrfFusion.ScoredChunk> fused = List.of(
            new RrfFusion.ScoredChunk(UUID.randomUUID(), 0.8d, "a"),
            new RrfFusion.ScoredChunk(UUID.randomUUID(), 0.61d, "b"),
            new RrfFusion.ScoredChunk(UUID.randomUUID(), 0.59d, "c")
        );

        List<RrfFusion.ScoredChunk> selected = evidenceSelector.select(fused, 5, 0.6d);
        assertThat(selected).hasSize(2);
        assertThat(selected).allMatch(row -> row.score() >= 0.6d);
    }
}
