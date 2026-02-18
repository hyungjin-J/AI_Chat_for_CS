package com.aichatbot.llm.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class LlmService {

    private final AppProperties appProperties;
    private final OllamaClient ollamaClient;
    private final MockLlmClient mockLlmClient;
    private final ObjectMapper objectMapper;

    public LlmService(
        AppProperties appProperties,
        OllamaClient ollamaClient,
        MockLlmClient mockLlmClient,
        ObjectMapper objectMapper
    ) {
        this.appProperties = appProperties;
        this.ollamaClient = ollamaClient;
        this.mockLlmClient = mockLlmClient;
        this.objectMapper = objectMapper;
    }

    public String generateAnswerContractJson(String prompt, String messageId) {
        String provider = appProperties.getLlm().getProvider();
        try {
            if ("mock".equalsIgnoreCase(provider)) {
                return mockLlmClient.generateContractJson(prompt);
            }
            if ("ollama".equalsIgnoreCase(provider)) {
                return ollamaClient.generateContractJson(prompt);
            }
            return buildSafeContract(0.0d, appProperties.getAnswer().getEvidenceThreshold());
        } catch (Exception exception) {
            return buildSafeContract(0.0d, appProperties.getAnswer().getEvidenceThreshold());
        }
    }

    private String buildSafeContract(double score, double threshold) {
        Map<String, Object> payload = Map.of(
            "schema_version", "v1",
            "response_type", "safe",
            "answer", Map.of("text", "확인 가능한 근거를 확보한 후 다시 안내드리겠습니다."),
            "citations", List.of(),
            "evidence", Map.of("score", score, "threshold", threshold)
        );
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("safe_contract_serialization_failed", exception);
        }
    }
}
