package com.aichatbot.rag.application;

import com.aichatbot.answer.application.AnswerContract;
import com.aichatbot.answer.application.AnswerContractValidator;
import com.aichatbot.answer.application.AnswerValidationResult;
import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ApiException;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.privacy.PiiMaskingService;
import com.aichatbot.llm.application.LlmService;
import com.aichatbot.rag.infrastructure.CitationRepository;
import com.aichatbot.rag.infrastructure.RagSearchLogRepository;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class RagAnswerService {

    private final RetrievalService retrievalService;
    private final RagSearchLogRepository ragSearchLogRepository;
    private final CitationRepository citationRepository;
    private final PiiMaskingService piiMaskingService;
    private final LlmService llmService;
    private final AnswerContractValidator answerContractValidator;
    private final AppProperties appProperties;

    public RagAnswerService(
        RetrievalService retrievalService,
        RagSearchLogRepository ragSearchLogRepository,
        CitationRepository citationRepository,
        PiiMaskingService piiMaskingService,
        LlmService llmService,
        AnswerContractValidator answerContractValidator,
        AppProperties appProperties
    ) {
        this.retrievalService = retrievalService;
        this.ragSearchLogRepository = ragSearchLogRepository;
        this.citationRepository = citationRepository;
        this.piiMaskingService = piiMaskingService;
        this.llmService = llmService;
        this.answerContractValidator = answerContractValidator;
        this.appProperties = appProperties;
    }

    public RetrievalResult retrieveAndStore(
        UUID retrieveId,
        UUID tenantId,
        UUID conversationId,
        String queryRaw,
        int topK,
        Map<String, String> filters,
        String traceId
    ) {
        String queryMasked = piiMaskingService.mask(queryRaw);
        RetrievalResult result = retrievalService.retrieve(new RagRetrievalRequest(
            tenantId,
            conversationId,
            queryMasked,
            topK,
            filters == null ? Map.of() : filters,
            traceId
        ));
        ragSearchLogRepository.save(tenantId, conversationId, queryMasked, topK, traceId, result.retrievalMode());
        persistCitations(tenantId, retrieveId, Instant.now(), result.evidenceChunks());
        return result;
    }

    public RagAnswerOutcome answer(
        UUID answerId,
        UUID tenantId,
        UUID conversationId,
        String queryRaw,
        int topK,
        Map<String, String> filters,
        String traceId
    ) {
        RetrievalResult result = retrieveAndStore(answerId, tenantId, conversationId, queryRaw, topK, filters, traceId);
        if (result.zeroEvidence()) {
            return RagAnswerOutcome.safe(answerId, "AI-009-200-SAFE", ErrorCatalog.messageOf("AI-009-200-SAFE"));
        }

        String prompt = buildPrompt(piiMaskingService.mask(queryRaw), answerId, result.evidenceChunks());
        String rawContractJson = llmService.generateAnswerContractJson(prompt, answerId.toString());
        AnswerValidationResult validation = answerContractValidator.validate(rawContractJson);
        if (!validation.valid()) {
            throw new ApiException(
                HttpStatus.UNPROCESSABLE_ENTITY,
                "AI-009-422-SCHEMA",
                ErrorCatalog.messageOf("AI-009-422-SCHEMA"),
                List.of("answer_contract_schema_invalid")
            );
        }
        if (validation.contract() == null || !"answer".equals(validation.contract().responseType())) {
            return RagAnswerOutcome.safe(answerId, "AI-009-200-SAFE", ErrorCatalog.messageOf("AI-009-200-SAFE"));
        }
        if (result.evidenceScore() < appProperties.getAnswer().getEvidenceThreshold()) {
            return RagAnswerOutcome.safe(answerId, "AI-009-409-EVIDENCE", ErrorCatalog.messageOf("AI-009-409-EVIDENCE"));
        }

        Set<String> allowedChunkIds = result.evidenceChunks().stream()
            .map(chunk -> chunk.chunkId().toString())
            .collect(Collectors.toSet());
        boolean hasUnknownCitation = validation.contract().citations().stream()
            .anyMatch(citation -> !allowedChunkIds.contains(citation.chunkId()));
        if (hasUnknownCitation) {
            throw new ApiException(
                HttpStatus.CONFLICT,
                "AI-009-409-CITATION",
                ErrorCatalog.messageOf("AI-009-409-CITATION"),
                List.of("citation_not_in_evidence_set")
            );
        }

        persistValidatedCitations(tenantId, answerId, Instant.now(), validation.contract().citations(), result.evidenceChunks());
        return RagAnswerOutcome.accepted(answerId);
    }

    private void persistCitations(UUID tenantId, UUID messageId, Instant createdAt, List<EvidenceChunk> chunks) {
        int rank = 1;
        for (EvidenceChunk chunk : chunks) {
            citationRepository.save(
                tenantId,
                messageId,
                createdAt,
                chunk.chunkId(),
                rank++,
                truncate(chunk.excerptMasked(), 240)
            );
        }
    }

    private void persistValidatedCitations(
        UUID tenantId,
        UUID messageId,
        Instant createdAt,
        List<AnswerContract.Citation> citations,
        List<EvidenceChunk> evidenceChunks
    ) {
        Map<String, EvidenceChunk> evidenceByChunkId = evidenceChunks.stream()
            .collect(Collectors.toMap(chunk -> chunk.chunkId().toString(), chunk -> chunk, (left, right) -> left));
        for (AnswerContract.Citation citation : citations) {
            EvidenceChunk chunk = evidenceByChunkId.get(citation.chunkId());
            String excerpt = chunk == null ? citation.excerptMasked() : chunk.excerptMasked();
            citationRepository.save(
                tenantId,
                messageId,
                createdAt,
                UUID.fromString(citation.chunkId()),
                citation.rankNo(),
                truncate(piiMaskingService.mask(excerpt), 240)
            );
        }
    }

    private String truncate(String text, int maxLength) {
        if (text == null) {
            return "";
        }
        String normalized = text.trim();
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, maxLength);
    }

    private String buildPrompt(String queryMasked, UUID answerId, List<EvidenceChunk> chunks) {
        StringBuilder builder = new StringBuilder();
        builder.append("Output JSON only for Answer Contract v1.\n");
        builder.append("message_id=").append(answerId).append("\n");
        builder.append("query=").append(queryMasked).append("\n");
        builder.append("Evidence:\n");
        for (EvidenceChunk chunk : chunks) {
            builder.append("- chunk_id=").append(chunk.chunkId())
                .append(", title=").append(chunk.title())
                .append(", version_no=").append(chunk.versionNo())
                .append(", rank_no=").append(chunk.rankNo())
                .append(", score=").append(chunk.score())
                .append(", original_chunk_text=").append(chunk.originalChunkText())
                .append("\n");
        }
        return builder.toString();
    }

    public record RagAnswerOutcome(boolean safeResponse, UUID id, String errorCode, String safeMessage) {
        static RagAnswerOutcome accepted(UUID id) {
            return new RagAnswerOutcome(false, id, null, null);
        }

        static RagAnswerOutcome safe(UUID id, String errorCode, String safeMessage) {
            return new RagAnswerOutcome(true, id, errorCode, safeMessage);
        }
    }
}
