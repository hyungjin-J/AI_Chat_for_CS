package com.aichatbot.contexts.knowledge.rag.application;

public interface KbEmbeddingGenerator {

    String generateEmbeddingVector(String embeddingInputText);
}
