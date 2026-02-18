package com.aichatbot.tool.application;

import com.aichatbot.global.privacy.PiiMaskingService;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.ai.chat.model.ToolContext;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

@Component
public class PolicyLookupTool {

    private static final Pattern TOPIC_PATTERN = Pattern.compile("^[a-zA-Z0-9_\\-\\s]{1,40}$");
    private static final Set<String> TOPIC_ALLOWLIST = Set.of("refund", "exchange", "delay", "delivery_delay", "general");

    private final PiiMaskingService piiMaskingService;

    public PolicyLookupTool(PiiMaskingService piiMaskingService) {
        this.piiMaskingService = piiMaskingService;
    }

    @Tool(description = "Lookup internal CS policy summary and return masked fields only.")
    public PolicyLookupResult lookupPolicy(
        @ToolParam(description = "Policy topic keyword. allowed: refund, exchange, delay, delivery_delay, general.") String topic,
        ToolContext toolContext
    ) {
        Map<String, Object> context = toolContext == null ? Map.of() : toolContext.getContext();
        String tenantKey = readContext(context, "tenant_key", "unknown");
        String traceId = readContext(context, "trace_id", "unknown-trace");
        String userRole = readContext(context, "user_role", "UNKNOWN");

        if (!("AGENT".equalsIgnoreCase(userRole) || "ADMIN".equalsIgnoreCase(userRole))) {
            throw new IllegalStateException("tool_context_role_not_allowed");
        }

        String normalized = normalize(topic);
        validateTopic(normalized);

        String policyCode;
        String policyVersion;
        String section;
        String sourceRef;
        String summary;
        String excerpt;

        if (normalized.contains("refund")) {
            normalized = "refund";
            policyCode = "POL-REFUND-001";
            policyVersion = "v2026.02";
            section = "refund_processing_tat";
            sourceRef = "kb://policy/refund/POL-REFUND-001";
            summary = "Refund requests are usually completed in 3-5 business days. Contact: refund-team@example.com";
            excerpt = "Refund processing target is 3-5 business days after intake.";
        } else if (normalized.contains("exchange")) {
            normalized = "exchange";
            policyCode = "POL-EXCHANGE-003";
            policyVersion = "v2026.02";
            section = "exchange_policy";
            sourceRef = "kb://policy/exchange/POL-EXCHANGE-003";
            summary = "Exchange requests require order status validation before intake.";
            excerpt = "Exchange is accepted after order status validation.";
        } else if (normalized.contains("delay")) {
            normalized = "delay";
            policyCode = "POL-DELIVERY-002";
            policyVersion = "v2026.02";
            section = "delivery_delay_compensation";
            sourceRef = "kb://policy/delivery/POL-DELIVERY-002";
            summary = "Delivery delay compensation depends on delay days and order status.";
            excerpt = "Delay compensation is calculated from delay days and order status.";
        } else {
            normalized = "general";
            policyCode = "POL-GENERAL-000";
            policyVersion = "v2026.02";
            section = "general_guidance";
            sourceRef = "kb://policy/general/POL-GENERAL-000";
            summary = "Use a more specific policy topic: refund, exchange, or delay.";
            excerpt = "Specific policy keywords improve lookup precision.";
        }

        String maskedSummary = piiMaskingService.mask(summary);
        String maskedExcerpt = piiMaskingService.mask(excerpt);
        UUID citationChunkId = UUID.nameUUIDFromBytes(
            (policyCode + "|" + policyVersion + "|" + section).getBytes(StandardCharsets.UTF_8)
        );

        return new PolicyLookupResult(
            normalized,
            policyCode,
            policyVersion,
            section,
            sourceRef,
            citationChunkId.toString(),
            maskedSummary,
            maskedExcerpt,
            traceId.startsWith("unknown") ? "unknown" : "ok",
            tenantKey.isBlank() ? "unknown" : "scoped"
        );
    }

    private String readContext(Map<String, Object> context, String key, String fallback) {
        Object value = context.get(key);
        if (value == null) {
            return fallback;
        }
        String stringValue = String.valueOf(value).trim();
        if (stringValue.isEmpty()) {
            return fallback;
        }
        return stringValue;
    }

    private String normalize(String raw) {
        if (raw == null) {
            return "";
        }
        return raw.toLowerCase(Locale.ROOT).trim();
    }

    private void validateTopic(String topic) {
        if (topic == null || topic.isBlank()) {
            throw new IllegalArgumentException("tool_topic_required");
        }
        if (!TOPIC_PATTERN.matcher(topic).matches()) {
            throw new IllegalArgumentException("tool_topic_invalid");
        }
        boolean allowlisted = TOPIC_ALLOWLIST.contains(topic)
            || topic.contains("refund")
            || topic.contains("exchange")
            || topic.contains("delay");
        if (!allowlisted) {
            throw new IllegalArgumentException("tool_topic_not_allowlisted");
        }
    }

    public record PolicyLookupResult(
        String topic,
        String policyCode,
        String policyVersion,
        String section,
        String sourceRef,
        String citationChunkId,
        String summaryMasked,
        String excerptMasked,
        String traceContextStatus,
        String tenantScope
    ) {
    }
}
