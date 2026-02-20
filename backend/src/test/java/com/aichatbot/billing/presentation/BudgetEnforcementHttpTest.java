package com.aichatbot.billing.presentation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0",
    "app.budget.input-token-max=5"
})
@AutoConfigureMockMvc
class BudgetEnforcementHttpTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        // Why: 각 테스트는 독립된 idempotency 키/세션을 사용하므로 별도 저장소 초기화 없이도 결정적으로 검증할 수 있다.
    }

    @Test
    void shouldReturn429WithStandardHeadersWhenTokenBudgetExceeded() throws Exception {
        String traceBudget = "88888888-8888-4888-8888-888888888888";
        String accessToken = login("agent1", "agent1-pass", "81111111-1111-4111-8111-111111111111");
        String sessionId = createSession(accessToken, "82222222-2222-4222-8222-222222222222");

        // Why: 표준 운영 경로(/v1)에서 예산 초과를 검증해야 레거시 경로 제거 후에도 정책이 유지됨을 보장할 수 있다.
        mockMvc.perform(post("/v1/sessions/{session_id}/messages", sessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceBudget)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-budget-" + traceBudget)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "text": "이 문장은 입력 토큰 예산을 넘기기 위해 충분히 길게 작성된 테스트 문장입니다.",
                      "top_k": 1,
                      "client_nonce": "nonce-budget"
                    }
                    """))
            .andExpect(status().isTooManyRequests())
            .andExpect(jsonPath("$.error_code").value("API-008-429-BUDGET"))
            .andExpect(jsonPath("$.trace_id").value(traceBudget))
            .andExpect(header().exists("Retry-After"))
            .andExpect(header().exists("X-RateLimit-Limit"))
            .andExpect(header().exists("X-RateLimit-Remaining"))
            .andExpect(header().exists("X-RateLimit-Reset"));
    }

    private String login(String loginId, String password, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-" + loginId + "-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "login_id": "%s",
                      "password": "%s",
                      "channel_id": "test",
                      "client_nonce": "nonce-login"
                    }
                    """.formatted(loginId, password)))
            .andExpect(status().isCreated())
            .andReturn();

        JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
        return json.get("access_token").asText();
    }

    private String createSession(String accessToken, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/sessions")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-session-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isCreated())
            .andReturn();

        JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
        return json.get("session_id").asText();
    }
}
