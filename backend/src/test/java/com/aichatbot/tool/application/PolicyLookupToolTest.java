package com.aichatbot.tool.application;

import com.aichatbot.global.privacy.PiiMaskingService;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.model.ToolContext;

import static org.assertj.core.api.Assertions.assertThat;

class PolicyLookupToolTest {

    @Test
    void shouldUseToolContextAndMaskPiiInToolResult() {
        PolicyLookupTool tool = new PolicyLookupTool(new PiiMaskingService());
        ToolContext toolContext = new ToolContext(Map.of(
            "tenant_key", "demo-tenant",
            "trace_id", "11111111-1111-4111-8111-111111111111",
            "user_role", "AGENT"
        ));

        PolicyLookupTool.PolicyLookupResult result = tool.lookupPolicy("refund", toolContext);

        assertThat(result.policyCode()).isEqualTo("POL-REFUND-001");
        assertThat(result.summaryMasked()).contains("***@***");
        assertThat(result.summaryMasked()).doesNotContain("refund-team@example.com");
        assertThat(result.traceContextStatus()).isEqualTo("ok");
        assertThat(result.tenantScope()).isEqualTo("scoped");
    }
}
