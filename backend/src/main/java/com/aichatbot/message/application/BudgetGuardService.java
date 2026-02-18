package com.aichatbot.message.application;

import com.aichatbot.global.config.AppProperties;
import com.aichatbot.global.error.ErrorCatalog;
import com.aichatbot.global.error.QuotaExceededException;
import com.aichatbot.session.infrastructure.ConversationRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class BudgetGuardService {

    private final AppProperties appProperties;
    private final ConversationRepository conversationRepository;

    public BudgetGuardService(AppProperties appProperties, ConversationRepository conversationRepository) {
        this.appProperties = appProperties;
        this.conversationRepository = conversationRepository;
    }

    public BudgetSnapshot enforcePreGeneration(UUID tenantId, UUID conversationId, String questionTextMasked, int topK) {
        int inputTokens = estimateTokens(questionTextMasked);
        int plannedOutputTokens = Math.min(appProperties.getBudget().getOutputTokenMax(), 400);
        int plannedToolCalls = 2;

        if (inputTokens > appProperties.getBudget().getInputTokenMax()) {
            throw budgetExceeded(appProperties.getBudget().getInputTokenMax(), 0L, "input_token_max");
        }

        if (topK > appProperties.getRag().getTopKMax()) {
            throw budgetExceeded(appProperties.getRag().getTopKMax(), 0L, "top_k_max");
        }

        if (plannedToolCalls > appProperties.getBudget().getToolCallMax()) {
            throw budgetExceeded(appProperties.getBudget().getToolCallMax(), 0L, "tool_call_max");
        }

        int sessionUsedTokens = conversationRepository.estimateSessionTokenUsage(tenantId, conversationId);
        int projected = sessionUsedTokens + inputTokens + plannedOutputTokens;
        if (projected > appProperties.getBudget().getSessionBudgetMax()) {
            long remaining = Math.max(0, appProperties.getBudget().getSessionBudgetMax() - sessionUsedTokens);
            throw budgetExceeded(appProperties.getBudget().getSessionBudgetMax(), remaining, "session_budget_max");
        }

        return new BudgetSnapshot(inputTokens, plannedOutputTokens, plannedToolCalls);
    }

    public void enforcePostGeneration(BudgetSnapshot snapshot, String answerTextMasked) {
        int outputTokens = estimateTokens(answerTextMasked);
        if (outputTokens > appProperties.getBudget().getOutputTokenMax()) {
            throw budgetExceeded(appProperties.getBudget().getOutputTokenMax(), 0L, "output_token_max");
        }
    }

    private int estimateTokens(String text) {
        if (text == null || text.isBlank()) {
            return 1;
        }
        return Math.max(1, text.trim().length() / 4);
    }

    private QuotaExceededException budgetExceeded(long limit, long remaining, String reason) {
        Instant reset = Instant.now().plus(30, ChronoUnit.SECONDS);
        return new QuotaExceededException(
            HttpStatus.TOO_MANY_REQUESTS,
            "API-008-429-BUDGET",
            ErrorCatalog.messageOf("API-008-429-BUDGET"),
            limit,
            remaining,
            reset.getEpochSecond(),
            30L
        );
    }
}
