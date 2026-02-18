package com.aichatbot.llm.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
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
        return invokeGenerate(prompt);
    }

    public String repairContractJson(String rawCandidate, String originalPrompt) {
        String repairPrompt = """
            Convert the candidate into strict Answer Contract v1 JSON only.
            Do not output prose or code fences.
            Required keys: schema_version,response_type,answer,citations,evidence.
            If response_type=answer then citations must contain at least 1 item.

            Candidate:
            %s

            Original question and evidence context:
            %s
            """.formatted(rawCandidate == null ? "" : rawCandidate, originalPrompt == null ? "" : originalPrompt);
        return invokeGenerate(repairPrompt);
    }

    private String invokeGenerate(String prompt) {
        String endpoint = appProperties.getLlm().getOllama().getBaseUrl() + "/api/generate";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> options = new LinkedHashMap<>();
        options.put("temperature", appProperties.getLlm().getOllama().getTemperature());
        options.put("top_p", appProperties.getLlm().getOllama().getTopP());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", appProperties.getLlm().getOllama().getModel());
        body.put("prompt", prompt);
        body.put("stream", false);
        body.put("format", "json");
        body.put("options", options);

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);
        String raw = restTemplate.postForObject(endpoint, request, String.class);
        if (raw == null || raw.isBlank()) {
            throw new IllegalStateException("empty_ollama_response");
        }

        try {
            JsonNode jsonNode = objectMapper.readTree(raw);
            if (jsonNode.has("response")) {
                return extractJsonPayload(jsonNode.get("response").asText(""));
            }
            throw new IllegalStateException("missing_response_field");
        } catch (Exception exception) {
            throw new IllegalStateException("invalid_ollama_response", exception);
        }
    }

    private String extractJsonPayload(String raw) {
        if (raw == null) {
            return "";
        }
        String candidate = raw.trim();
        if (candidate.startsWith("```")) {
            candidate = candidate.replaceAll("(?s)^```(?:json)?\\s*", "");
            candidate = candidate.replaceAll("\\s*```$", "");
            candidate = candidate.trim();
        }
        int first = candidate.indexOf('{');
        int last = candidate.lastIndexOf('}');
        if (first >= 0 && last > first) {
            return candidate.substring(first, last + 1);
        }
        return candidate;
    }
}
