package com.aichatbot.answer.application;

import java.util.List;

public record AnswerContract(
    String schemaVersion,
    String responseType,
    Answer answer,
    List<Citation> citations,
    Evidence evidence
) {

    public record Answer(String text) {
    }

    public record Citation(
        String citationId,
        String messageId,
        String chunkId,
        int rankNo,
        String excerptMasked
    ) {
    }

    public record Evidence(double score, double threshold) {
    }
}
