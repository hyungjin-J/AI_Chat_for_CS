package com.aichatbot.message.application;

import com.aichatbot.answer.application.AnswerContract;
import com.aichatbot.answer.application.AnswerContractValidator;
import com.aichatbot.answer.application.AnswerValidationResult;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.observability.TraceGuard;
import com.aichatbot.global.privacy.PiiMaskingService;
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

        int topK = resolveTopK(requestedTopK);
        BudgetSnapshot budgetSnapshot = budgetGuardService.enforcePreGeneration(tenantId, sessionId, questionMasked, topK);

        MessageView questionMessage = messageRepository.create(
            tenantId,
            sessionId,
            "AGENT",
            questionMasked,
            traceId
        );

        RetrievalResult retrievalResult = retrievalService.retrieve(questionMasked, tenantId, topK);
        ragSearchLogRepository.save(
            tenantId,
            sessionId,
            questionMasked,
            topK,
            traceId,
            retrievalResult.retrievalMode()
        );

        String prompt = buildLlmPrompt(questionMasked, questionMessage.id(), retrievalResult.evidenceChunks());
        String rawContractJson = llmService.generateAnswerContractJson(prompt, questionMessage.id().toString());
        AnswerValidationResult validation = answerContractValidator.validate(rawContractJson);

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
            for (EvidenceChunk chunk : retrievalResult.evidenceChunks()) {
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
                        "excerpt_masked", excerptMasked
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

    private String buildLlmPrompt(String questionMasked, UUID messageId, List<EvidenceChunk> evidenceChunks) {
        StringBuilder builder = new StringBuilder();
        builder.append("당신은 CS 상담 보조 모델입니다. 반드시 JSON만 출력하세요. 설명 금지.\n");
        builder.append("스키마는 schema_version=v1, response_type, answer.text, citations[], evidence(score,threshold)를 포함해야 합니다.\n");
        builder.append("response_type=answer인 경우 citations는 1개 이상이어야 합니다.\n");
        builder.append("message_id 필드는 ").append(messageId).append(" 를 사용하세요.\n");
        builder.append("evidence.threshold는 ").append(appProperties.getAnswer().getEvidenceThreshold()).append(" 로 출력하세요.\n");
        builder.append("질문(마스킹됨): ").append(questionMasked).append("\n");
        builder.append("근거 목록:\n");
        for (EvidenceChunk chunk : evidenceChunks) {
            builder.append("- chunk_id=").append(chunk.chunkId())
                .append(", rank=").append(chunk.rankNo())
                .append(", text=").append(chunk.chunkTextMasked())
                .append("\n");
        }
        builder.append("정책 위반 우려가 있거나 근거가 부족하면 response_type=safe로 출력하세요.");
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
}
