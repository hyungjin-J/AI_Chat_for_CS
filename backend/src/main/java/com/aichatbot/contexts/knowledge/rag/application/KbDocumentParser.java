package com.aichatbot.contexts.knowledge.rag.application;

import java.util.List;

public interface KbDocumentParser {

    List<String> parseMaskedContent(String rawContentMasked);
}
