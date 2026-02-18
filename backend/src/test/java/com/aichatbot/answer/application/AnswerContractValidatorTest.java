package com.aichatbot.answer.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class AnswerContractValidatorTest {

    private final AppProperties appProperties = new AppProperties();
    private final ObjectMapper objectMapper = new ObjectMapper()
        .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    private final AnswerContractValidator validator = new AnswerContractValidator(objectMapper, appProperties);

    @Test
    void shouldPassWhenSchemaCitationAndEvidenceAreValid() {
        String payload = """
            {
              "schema_version": "v1",
              "response_type": "answer",
              "answer": {"text": "정상 응답"},
              "citations": [
                {
                  "citation_id": "c1",
                  "message_id": "11111111-1111-1111-1111-111111111111",
                  "chunk_id": "22222222-2222-2222-2222-222222222222",
                  "rank_no": 1,
                  "excerpt_masked": "근거"
                }
              ],
              "evidence": {"score": 0.9, "threshold": 0.7}
            }
            """;

        AnswerValidationResult result = validator.validate(payload);

        assertThat(result.valid()).isTrue();
        assertThat(result.errorCode()).isNull();
    }

    @Test
    void shouldFailWithCitationCodeWhenAnswerHasNoCitations() {
        String payload = """
            {
              "schema_version": "v1",
              "response_type": "answer",
              "answer": {"text": "근거 없음"},
              "citations": [],
              "evidence": {"score": 0.8, "threshold": 0.7}
            }
            """;

        AnswerValidationResult result = validator.validate(payload);

        assertThat(result.valid()).isFalse();
        assertThat(result.errorCode()).isEqualTo("AI-009-409-CITATION");
    }

    @Test
    void shouldFailWithEvidenceCodeWhenScoreBelowThreshold() {
        String payload = """
            {
              "schema_version": "v1",
              "response_type": "answer",
              "answer": {"text": "점수 미달"},
              "citations": [
                {
                  "citation_id": "c1",
                  "message_id": "11111111-1111-1111-1111-111111111111",
                  "chunk_id": "22222222-2222-2222-2222-222222222222",
                  "rank_no": 1,
                  "excerpt_masked": "근거"
                }
              ],
              "evidence": {"score": 0.2, "threshold": 0.7}
            }
            """;

        AnswerValidationResult result = validator.validate(payload);

        assertThat(result.valid()).isFalse();
        assertThat(result.errorCode()).isEqualTo("AI-009-409-EVIDENCE");
    }
}
