package com.aichatbot.answer.application;

import com.aichatbot.global.config.AppProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.io.InputStream;
import java.util.List;
import java.util.Set;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

@Component
public class AnswerContractValidator {

    private final ObjectMapper objectMapper;
    private final AppProperties appProperties;
    private final JsonSchema schema;

    public AnswerContractValidator(ObjectMapper objectMapper, AppProperties appProperties) {
        this.objectMapper = objectMapper;
        this.appProperties = appProperties;
        this.schema = loadSchema();
    }

    public AnswerValidationResult validate(String rawJson) {
        try {
            JsonNode jsonNode = objectMapper.readTree(rawJson);
            Set<ValidationMessage> violations = schema.validate(jsonNode);
            if (!violations.isEmpty()) {
                return new AnswerValidationResult(false, "AI-009-422-SCHEMA", null);
            }

            AnswerContract contract = objectMapper.treeToValue(jsonNode, AnswerContract.class);
            if (contract == null) {
                return new AnswerValidationResult(false, "AI-009-422-SCHEMA", null);
            }

            boolean answerType = "answer".equals(contract.responseType());
            List<AnswerContract.Citation> citations = contract.citations() == null ? List.of() : contract.citations();
            if (answerType && citations.isEmpty()) {
                return new AnswerValidationResult(false, "AI-009-409-CITATION", contract);
            }

            double configuredThreshold = appProperties.getAnswer().getEvidenceThreshold();
            double threshold = Math.max(contract.evidence().threshold(), configuredThreshold);
            if (answerType && contract.evidence().score() < threshold) {
                return new AnswerValidationResult(false, "AI-009-409-EVIDENCE", contract);
            }

            return new AnswerValidationResult(true, null, contract);
        } catch (Exception exception) {
            return new AnswerValidationResult(false, "AI-009-422-SCHEMA", null);
        }
    }

    private JsonSchema loadSchema() {
        try {
            JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);
            InputStream schemaStream = new ClassPathResource("schemas/answer_contract_v1.json").getInputStream();
            return factory.getSchema(schemaStream);
        } catch (Exception exception) {
            throw new IllegalStateException("answer_contract_schema_load_failed", exception);
        }
    }
}
