package com.aichatbot.rag.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class RrfFusionTest {

    private final RrfFusion rrfFusion = new RrfFusion();

    @Test
    void shouldProduceDeterministicOrderWhenScoresAreEqual() {
        UUID a = UUID.fromString("10000000-0000-0000-0000-000000000001");
        UUID b = UUID.fromString("10000000-0000-0000-0000-000000000002");

        List<RrfFusion.ScoredChunk> vector = List.of(
            new RrfFusion.ScoredChunk(a, 0.9d, "a"),
            new RrfFusion.ScoredChunk(b, 0.8d, "b")
        );
        List<RrfFusion.ScoredChunk> bm25 = List.of(
            new RrfFusion.ScoredChunk(b, 0.9d, "b"),
            new RrfFusion.ScoredChunk(a, 0.8d, "a")
        );

        List<RrfFusion.ScoredChunk> first = rrfFusion.fuse(vector, bm25, 60);
        List<RrfFusion.ScoredChunk> second = rrfFusion.fuse(vector, bm25, 60);

        assertThat(first).hasSize(2);
        assertThat(first).isEqualTo(second);
    }
}
