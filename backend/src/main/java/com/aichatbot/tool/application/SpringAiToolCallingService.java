package com.aichatbot.tool.application;

import com.aichatbot.tool.application.PolicyLookupTool.PolicyLookupResult;
import java.util.Map;
import java.util.UUID;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.stereotype.Service;

@Service
public class SpringAiToolCallingService {

    private final PolicyLookupTool policyLookupTool;

    public SpringAiToolCallingService(PolicyLookupTool policyLookupTool) {
        this.policyLookupTool = policyLookupTool;
    }

    public ToolExecutionResult maybeCallPolicyLookup(
        String questionMasked,
        UUID tenantId,
        String traceId,
        String userRole,
        String tenantKey
    ) {
        if (!shouldInvoke(questionMasked)) {
            return ToolExecutionResult.notInvoked();
        }
        if (!isAllowedRole(userRole)) {
            return ToolExecutionResult.failed(
                "policy_lookup",
                UUID.randomUUID().toString(),
                "Policy lookup was skipped because caller role is not allowed."
            );
        }

        String topic = inferTopic(questionMasked);
        String toolRunId = UUID.randomUUID().toString();
        try {
            ToolContext toolContext = new ToolContext(Map.of(
                "tenant_key", tenantKey,
                "tenant_id", tenantId.toString(),
                "trace_id", traceId,
                "user_role", userRole
            ));

            PolicyLookupResult result = policyLookupTool.lookupPolicy(topic, toolContext);
            return ToolExecutionResult.completed(
                "policy_lookup",
                toolRunId,
                result.policyCode(),
                result.policyVersion(),
                result.section(),
                result.sourceRef(),
                result.citationChunkId(),
                result.summaryMasked(),
                result.excerptMasked()
            );
        } catch (Exception exception) {
            return ToolExecutionResult.failed(
                "policy_lookup",
                toolRunId,
                "Policy lookup failed and was not used in final answer context."
            );
        }
    }

    private boolean isAllowedRole(String userRole) {
        if (userRole == null) {
            return false;
        }
        return "AGENT".equalsIgnoreCase(userRole) || "ADMIN".equalsIgnoreCase(userRole);
    }

    private boolean shouldInvoke(String questionMasked) {
        if (questionMasked == null || questionMasked.isBlank()) {
            return false;
        }
        String normalized = questionMasked.toLowerCase();
        return normalized.contains("refund")
            || normalized.contains("policy")
            || normalized.contains("exchange")
            || normalized.contains("delay")
            || normalized.contains("delivery");
    }

    private String inferTopic(String questionMasked) {
        String normalized = questionMasked == null ? "" : questionMasked.toLowerCase();
        if (normalized.contains("refund")) {
            return "refund";
        }
        if (normalized.contains("exchange")) {
            return "exchange";
        }
        if (normalized.contains("delivery") || normalized.contains("delay")) {
            return "delay";
        }
        return "general";
    }

    public record ToolExecutionResult(
        boolean invoked,
        String toolName,
        String toolRunId,
        String status,
        String policyCode,
        String policyVersion,
        String section,
        String sourceRef,
        String citationChunkId,
        String summaryMasked,
        String excerptMasked
    ) {

        public static ToolExecutionResult notInvoked() {
            return new ToolExecutionResult(false, "policy_lookup", "", "skipped", "", "", "", "", "", "", "");
        }

        public static ToolExecutionResult completed(
            String toolName,
            String toolRunId,
            String policyCode,
            String policyVersion,
            String section,
            String sourceRef,
            String citationChunkId,
            String summaryMasked,
            String excerptMasked
        ) {
            return new ToolExecutionResult(
                true,
                toolName,
                toolRunId,
                "completed",
                policyCode,
                policyVersion,
                section,
                sourceRef,
                citationChunkId,
                summaryMasked,
                excerptMasked
            );
        }

        public static ToolExecutionResult failed(String toolName, String toolRunId, String summaryMasked) {
            return new ToolExecutionResult(
                true,
                toolName,
                toolRunId,
                "failed",
                "",
                "",
                "",
                "",
                "",
                summaryMasked,
                ""
            );
        }

        public boolean hasPromptContext() {
            return invoked && "completed".equals(status) && summaryMasked != null && !summaryMasked.isBlank();
        }

        public boolean hasCitationChunk() {
            return invoked
                && "completed".equals(status)
                && citationChunkId != null
                && !citationChunkId.isBlank()
                && excerptMasked != null
                && !excerptMasked.isBlank();
        }
    }
}
