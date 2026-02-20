package com.aichatbot.rag.application;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

@Component
public class RagIdempotencyRegistry {

    private final Map<String, String> keyToObjectId = new ConcurrentHashMap<>();

    public String getOrCreate(String scope, String idempotencyKey, java.util.function.Supplier<String> idSupplier) {
        String key = scope + ":" + idempotencyKey;
        return keyToObjectId.computeIfAbsent(key, ignored -> idSupplier.get());
    }
}
