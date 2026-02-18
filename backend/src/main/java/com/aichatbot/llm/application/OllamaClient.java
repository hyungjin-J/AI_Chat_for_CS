package com.aichatbot.llm.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class OllamaClient implements LlmClient {

    private final AppProperties appProperties;
    private final ObjectMapper objectMapper;
    private final RestTemplate restTemplate;

    public OllamaClient(AppProperties appProperties, ObjectMapper objectMapper, RestTemplateBuilder restTemplateBuilder) {
        this.appProperties = appProperties;
        this.objectMapper = objectMapper;
        this.restTemplate = restTemplateBuilder.build();
    }

    @Override
    public String generateContractJson(String prompt) {
        String endpoint = appProperties.getLlm().getOllama().getBaseUrl() + "/api/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = Map.of(
            "model", appProperties.getLlm().getOllama().getModel(),
            "prompt", prompt,
            "stream", false
        );

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);
        String raw = restTemplate.postForObject(endpoint, request, String.class);
        if (raw == null || raw.isBlank()) {
            throw new IllegalStateException("empty_ollama_response");
        }

        try {
            JsonNode jsonNode = objectMapper.readTree(raw);
            if (jsonNode.has("response")) {
                return jsonNode.get("response").asText("");
            }
            throw new IllegalStateException("missing_response_field");
        } catch (Exception exception) {
            throw new IllegalStateException("invalid_ollama_response", exception);
        }
    }
}
