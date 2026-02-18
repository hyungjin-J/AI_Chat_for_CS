package com.aichatbot.message.application;

import com.aichatbot.answer.application.AnswerContract;
import com.aichatbot.answer.application.AnswerContractValidator;
import com.aichatbot.answer.application.AnswerValidationResult;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.privacy.PiiMaskingService;
import com.aichatbot.global.security.PrincipalUtils;
import com.aichatbot.llm.application.LlmService;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.message.infrastructure.StreamEventRepository;
import com.aichatbot.rag.application.EvidenceChunk;
import com.aichatbot.rag.application.GuardrailPolicyService;
import com.aichatbot.rag.application.RetrievalResult;
import com.aichatbot.rag.application.RetrievalService;
import com.aichatbot.rag.infrastructure.CitationRepository;
import com.aichatbot.rag.infrastructure.RagSearchLogRepository;
import com.aichatbot.session.infrastructure.ConversationRepository;
import com.aichatbot.tool.application.SpringAiToolCallingService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;

@Service
public class MessageGenerationService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final StreamEventRepository streamEventRepository;
    private final RagSearchLogRepository ragSearchLogRepository;
    private final CitationRepository citationRepository;
    private final RetrievalService retrievalService;
    private final GuardrailPolicyService guardrailPolicyService;
    private final LlmService llmService;
    private final AnswerContractValidator answerContractValidator;
    private final PiiMaskingService piiMaskingService;
    private final SpringAiToolCallingService springAiToolCallingService;
    private final BudgetGuardService budgetGuardService;
    private final MvpObservabilityMetrics mvpObservabilityMetrics;
    private final AppProperties appProperties;
    private final ObjectMapper objectMapper;

    public MessageGenerationService(
        ConversationRepository conversationRepository,
        MessageRepository messageRepository,
        StreamEventRepository streamEventRepository,
        RagSearchLogRepository ragSearchLogRepository,
        CitationRepository citationRepository,
        RetrievalService retrievalService,
        GuardrailPolicyService guardrailPolicyService,
        LlmService llmService,
        AnswerContractValidator answerContractValidator,
        PiiMaskingService piiMaskingService,
        SpringAiToolCallingService springAiToolCallingService,
        BudgetGuardService budgetGuardService,
        MvpObservabilityMetrics mvpObservabilityMetrics,
        AppProperties appProperties,
        ObjectMapper objectMapper
    ) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.streamEventRepository = streamEventRepository;
        this.ragSearchLogRepository = ragSearchLogRepository;
        this.citationRepository = citationRepository;
        this.retrievalService = retrievalService;
        this.guardrailPolicyService = guardrailPolicyService;
        this.llmService = llmService;
        this.answerContractValidator = answerContractValidator;
        this.piiMaskingService = piiMaskingService;
        this.springAiToolCallingService = springAiToolCallingService;
        this.budgetGuardService = budgetGuardService;
        this.mvpObservabilityMetrics = mvpObservabilityMetrics;
        this.appProperties = appProperties;
        this.objectMapper = objectMapper;
    }

    public MessageGenerationResult generate(UUID tenantId, UUID sessionId, String questionTextRaw, Integer requestedTopK) {
        TraceGuard.requireTraceId();
        String traceId = TraceGuard.requireTraceId();

        conversationRepository.findById(tenantId, sessionId).orElseThrow(() ->
            new IllegalArgumentException("conversation_not_found")
        );

        String questionMasked = piiMaskingService.mask(questionTextRaw);
        guardrailPolicyService.enforceInputPolicy(questionMasked);
        String userRole = resolvePrimaryRole();

        int topK = resolveTopK(requestedTopK);
        BudgetSnapshot budgetSnapshot = budgetGuardService.enforcePreGeneration(tenantId, sessionId, questionMasked, topK);

        MessageView questionMessage = messageRepository.create(
            tenantId,
            sessionId,
            "AGENT",
            questionMasked,
            traceId
        );

        SpringAiToolCallingService.ToolExecutionResult toolExecution = springAiToolCallingService.maybeCallPolicyLookup(
            questionMasked,
            tenantId,
            traceId,
            userRole,
            com.aichatbot.global.tenant.TenantContext.getTenantKey()
        );

        RetrievalResult retrievalResult = retrievalService.retrieve(questionMasked, tenantId, topK);
        List<EvidenceChunk> allEvidenceChunks = new ArrayList<>(retrievalResult.evidenceChunks());
        if (toolExecution.hasCitationChunk()) {
            allEvidenceChunks.add(new EvidenceChunk(
                UUID.fromString(toolExecution.citationChunkId()),
                piiMaskingService.mask(toolExecution.excerptMasked()),
                allEvidenceChunks.size() + 1,
                0.90d
            ));
        }
        ragSearchLogRepository.save(
            tenantId,
            sessionId,
            questionMasked,
            topK,
            traceId,
            retrievalResult.retrievalMode()
        );

        List<String> toolHints = new ArrayList<>();
        if (toolExecution.hasPromptContext()) {
            toolHints.add(toolExecution.summaryMasked());
        }

        String prompt = buildLlmPrompt(questionMasked, questionMessage.id(), allEvidenceChunks, toolHints);
        String rawContractJson = llmService.generateAnswerContractJson(prompt, questionMessage.id().toString());
        AnswerValidationResult validation = answerContractValidator.validate(rawContractJson);
        if (!validation.valid()) {
            String repaired = llmService.repairAnswerContractJson(rawContractJson, prompt, questionMessage.id().toString());
            validation = answerContractValidator.validate(repaired);
        }

        boolean safeResponse = !validation.valid() || retrievalResult.evidenceChunks().isEmpty();
        String validationErrorCode = validation.errorCode();
        String finalAnswerText;
        double threshold = appProperties.getAnswer().getEvidenceThreshold();

        List<AnswerContract.Citation> citationsForAnswer = new ArrayList<>();
        if (!safeResponse && validation.contract() != null && "answer".equals(validation.contract().responseType())) {
            if (retrievalResult.evidenceScore() < threshold) {
                safeResponse = true;
                validationErrorCode = "AI-009-409-EVIDENCE";
            } else {
                Set<String> allowedChunkIds = retrievalResult.evidenceChunks().stream()
                    .map(chunk -> chunk.chunkId().toString())
                    .collect(Collectors.toSet());
                if (toolExecution.hasCitationChunk()) {
                    allowedChunkIds.add(toolExecution.citationChunkId());
                }
                boolean hasUnknownCitation = validation.contract().citations().stream()
                    .anyMatch(citation -> !allowedChunkIds.contains(citation.chunkId()));
                if (hasUnknownCitation) {
                    safeResponse = true;
                    validationErrorCode = "AI-009-409-CITATION";
                }
            }
        }

        if (!safeResponse && validation.contract() != null && "answer".equals(validation.contract().responseType())) {
            finalAnswerText = piiMaskingService.mask(validation.contract().answer().text());
            budgetGuardService.enforcePostGeneration(budgetSnapshot, finalAnswerText);
            citationsForAnswer.addAll(validation.contract().citations());
            attachToolCitationIfMissing(citationsForAnswer, questionMessage.id(), toolExecution);
        } else {
            safeResponse = true;
            validationErrorCode = validationErrorCode == null ? "AI-009-200-SAFE" : validationErrorCode;
            finalAnswerText = ErrorCatalog.messageOf("AI-009-200-SAFE");
        }

        mvpObservabilityMetrics.recordGenerationOutcome(safeResponse, citationsForAnswer.size());

        MessageView answerMessage = messageRepository.create(
            tenantId,
            sessionId,
            "ASSISTANT",
            finalAnswerText,
            traceId
        );

        int eventSeq = 1;
        if (toolExecution.invoked()) {
            Map<String, Object> toolPayload = new HashMap<>();
            toolPayload.put("tool_name", toolExecution.toolName());
            toolPayload.put("tool_run_id", toolExecution.toolRunId());
            toolPayload.put("status", toolExecution.status());
            toolPayload.put("policy_code", toolExecution.policyCode());
            toolPayload.put("policy_version", toolExecution.policyVersion());
            toolPayload.put("section", toolExecution.section());
            toolPayload.put("source_ref", toolExecution.sourceRef());
            toolPayload.put("summary_masked", piiMaskingService.mask(toolExecution.summaryMasked()));
            toolPayload.put("trace_id", traceId);

            streamEventRepository.save(
                tenantId,
                answerMessage.id(),
                answerMessage.createdAt(),
                eventSeq++,
                "tool",
                toJson(toolPayload)
            );
        }

        streamEventRepository.save(
            tenantId,
            answerMessage.id(),
            answerMessage.createdAt(),
            eventSeq++,
            "tool",
            toJson(Map.of(
                "tool_name", "rag_retrieve",
                "status", "completed",
                "retrieval_mode", retrievalResult.retrievalMode(),
                "trace_id", traceId
            ))
        );

        if (!safeResponse) {
            Map<UUID, EvidenceChunk> evidenceById = new HashMap<>();
            for (EvidenceChunk chunk : allEvidenceChunks) {
                evidenceById.put(chunk.chunkId(), chunk);
            }

            for (AnswerContract.Citation citation : citationsForAnswer) {
                UUID chunkId = UUID.fromString(citation.chunkId());
                EvidenceChunk matchedChunk = evidenceById.get(chunkId);
                String excerptMasked = piiMaskingService.mask(
                    matchedChunk == null ? citation.excerptMasked() : matchedChunk.chunkTextMasked()
                );
                citationRepository.save(
                    tenantId,
                    answerMessage.id(),
                    answerMessage.createdAt(),
                    chunkId,
                    citation.rankNo(),
                    excerptMasked
                );
                streamEventRepository.save(
                    tenantId,
                    answerMessage.id(),
                    answerMessage.createdAt(),
                    eventSeq++,
                    "citation",
                    toJson(Map.of(
                        "message_id", answerMessage.id().toString(),
                        "chunk_id", chunkId.toString(),
                        "rank_no", citation.rankNo(),
                        "excerpt_masked", excerptMasked,
                        "citation_type", toolExecution.hasCitationChunk()
                            && toolExecution.citationChunkId().equals(chunkId.toString()) ? "TOOL_CITATION" : "RAG_CITATION"
                    ))
                );
            }

            List<String> chunks = chunkTokens(finalAnswerText);
            for (String chunk : chunks) {
                streamEventRepository.save(
                    tenantId,
                    answerMessage.id(),
                    answerMessage.createdAt(),
                    eventSeq++,
                    "token",
                    toJson(Map.of("text", chunk))
                );
            }
        } else {
            streamEventRepository.save(
                tenantId,
                answerMessage.id(),
                answerMessage.createdAt(),
                eventSeq++,
                "safe_response",
                toJson(Map.of(
                    "error_code", "AI-009-200-SAFE",
                    "message", ErrorCatalog.messageOf("AI-009-200-SAFE")
                ))
            );
            if (validationErrorCode != null && !"AI-009-200-SAFE".equals(validationErrorCode)) {
                streamEventRepository.save(
                    tenantId,
                    answerMessage.id(),
                    answerMessage.createdAt(),
                    eventSeq++,
                    "error",
                    toJson(Map.of(
                        "error_code", validationErrorCode,
                        "message", ErrorCatalog.messageOf(validationErrorCode),
                        "trace_id", traceId
                    ))
                );
            }
        }

        streamEventRepository.save(
            tenantId,
            answerMessage.id(),
            answerMessage.createdAt(),
            eventSeq,
            "done",
            toJson(Map.of(
                "message_id", answerMessage.id().toString(),
                "trace_id", traceId,
                "response_type", safeResponse ? "safe" : "answer"
            ))
        );

        return new MessageGenerationResult(
            questionMessage.id().toString(),
            answerMessage.id().toString(),
            safeResponse,
            validationErrorCode
        );
    }

    private int resolveTopK(Integer requestedTopK) {
        if (requestedTopK == null || requestedTopK <= 0) {
            return appProperties.getRag().getTopKDefault();
        }
        return Math.min(requestedTopK, appProperties.getRag().getTopKMax());
    }
    private String buildLlmPrompt(
        String questionMasked,
        UUID messageId,
        List<EvidenceChunk> evidenceChunks,
        List<String> toolHints
    ) {
        StringBuilder builder = new StringBuilder();
        builder.append("You are a CS support model. Output JSON only and no prose.\n");
        builder.append("Answer Contract v1 required fields: schema_version,response_type,answer,citations,evidence.\n");
        builder.append("If response_type is answer, citations must contain at least one item.\n");
        builder.append("Use exactly this message_id: ").append(messageId).append("\n");
        builder.append("Set evidence.threshold to ").append(appProperties.getAnswer().getEvidenceThreshold()).append(".\n");
        builder.append("Question (masked): ").append(questionMasked).append("\n");
        if (toolHints != null && !toolHints.isEmpty()) {
            builder.append("Tool findings (masked):\n");
            for (String toolHint : toolHints) {
                builder.append("- ").append(toolHint).append("\n");
            }
        }
        builder.append("Evidence chunks:\n");
        for (EvidenceChunk chunk : evidenceChunks) {
            builder.append("- chunk_id=").append(chunk.chunkId())
                .append(", rank=").append(chunk.rankNo())
                .append(", text=").append(chunk.chunkTextMasked())
                .append("\n");
        }
        builder.append("Output example: ");
        builder.append("{\"schema_version\":\"v1\",\"response_type\":\"answer\",\"answer\":{\"text\":\"...\"},");
        builder.append("\"citations\":[{\"citation_id\":\"c1\",\"message_id\":\"").append(messageId).append("\",");
        builder.append("\"chunk_id\":\"<chunk_id from evidence>\",\"rank_no\":1,\"excerpt_masked\":\"...\"}],");
        builder.append("\"evidence\":{\"score\":0.9,\"threshold\":").append(appProperties.getAnswer().getEvidenceThreshold()).append("}}\n");
        builder.append("If insufficient evidence, return response_type=safe with empty citations.");
        return builder.toString();
    }
    private List<String> chunkTokens(String answerText) {
        String normalized = answerText == null ? "" : answerText.trim();
        if (normalized.isEmpty()) {
            return List.of("");
        }

        String[] words = normalized.split("\\s+");
        List<String> chunks = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (String word : words) {
            if (current.length() + word.length() + 1 > 30) {
                chunks.add(current.toString().trim());
                current = new StringBuilder();
            }
            current.append(word).append(' ');
        }

        if (current.length() > 0) {
            chunks.add(current.toString().trim());
        }

        return chunks;
    }

    private String toJson(Map<String, Object> payload) {
        try {
            return objectMapper.writeValueAsString(payload);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("stream_payload_serialization_failed", exception);
        }
    }

    private String resolvePrimaryRole() {
        List<String> roles = PrincipalUtils.currentPrincipal().roles();
        if (roles == null || roles.isEmpty()) {
            return "AGENT";
        }
        return roles.get(0);
    }

    private void attachToolCitationIfMissing(
        List<AnswerContract.Citation> citationsForAnswer,
        UUID questionMessageId,
        SpringAiToolCallingService.ToolExecutionResult toolExecution
    ) {
        if (!toolExecution.hasCitationChunk()) {
            return;
        }
        boolean alreadyMapped = citationsForAnswer.stream()
            .anyMatch(citation -> toolExecution.citationChunkId().equals(citation.chunkId()));
        if (alreadyMapped) {
            return;
        }
        int nextRank = citationsForAnswer.stream()
            .mapToInt(AnswerContract.Citation::rankNo)
            .max()
            .orElse(0) + 1;
        citationsForAnswer.add(new AnswerContract.Citation(
            "tool-" + toolExecution.toolRunId(),
            questionMessageId.toString(),
            toolExecution.citationChunkId(),
            nextRank,
            piiMaskingService.mask(toolExecution.excerptMasked())
        ));
    }
}


