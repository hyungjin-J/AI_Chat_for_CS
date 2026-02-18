package com.aichatbot.llm.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class MockLlmClient implements LlmClient {

    private static final Pattern MESSAGE_ID_PATTERN = Pattern.compile("message_id 필드는\\s+([0-9a-fA-F\\-]{36})");
    private static final Pattern CHUNK_ID_PATTERN = Pattern.compile("chunk_id=([0-9a-fA-F\\-]{36})");

    private final ObjectMapper objectMapper;
    private final AppProperties appProperties;

    public MockLlmClient(ObjectMapper objectMapper, AppProperties appProperties) {
        this.objectMapper = objectMapper;
        this.appProperties = appProperties;
    }

    @Override
    public String generateContractJson(String prompt) {
        String messageId = extract(MESSAGE_ID_PATTERN, prompt, UUID.randomUUID().toString());
        String chunkId = extract(CHUNK_ID_PATTERN, prompt, "30000000-0000-0000-0000-000000000005");
        double threshold = appProperties.getAnswer().getEvidenceThreshold();

        Map<String, Object> payload = Map.of(
            "schema_version", "v1",
            "response_type", "answer",
            "answer", Map.of("text", "환불 정책 안내: 접수 후 영업일 3~5일 내 환불되며 상태를 확인해 드립니다."),
            "citations", List.of(Map.of(
                "citation_id", "demo-citation-1",
                "message_id", messageId,
                "chunk_id", chunkId,
                "rank_no", 1,
                "excerpt_masked", "문의는 ***@*** 로 접수할 수 있습니다."
            )),
            "evidence", Map.of(
                "score", 0.95d,
                "threshold", threshold
            )
        );
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("mock_contract_serialization_failed", exception);
        }
    }

    private String extract(Pattern pattern, String input, String fallback) {
        Matcher matcher = pattern.matcher(input == null ? "" : input);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return fallback;
    }
}
