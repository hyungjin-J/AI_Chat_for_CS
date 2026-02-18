package com.aichatbot.message.presentation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "spring.task.scheduling.enabled=false")
@AutoConfigureMockMvc
class MessageFlowContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldFailClosedAndStreamSafeResponseBeforeDone() throws Exception {
        String traceLogin = "11111111-1111-4111-8111-111111111111";
        String traceSession = "22222222-2222-4222-8222-222222222222";
        String traceMessage = "33333333-3333-4333-8333-333333333333";
        String traceStream = "44444444-4444-4444-8444-444444444444";

        String accessToken = login("agent1", "agent1-pass", traceLogin);
        String sessionId = createSession(accessToken, traceSession);

        MvcResult messageResult = mockMvc.perform(post("/v1/sessions/{session_id}/messages", sessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceMessage)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-message-agent")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "text": "zzzzzz qqqqq",
                      "top_k": 1,
                      "client_nonce": "nonce-1"
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.trace_id").value(traceMessage))
            .andReturn();

        String answerId = objectMapper.readTree(messageResult.getResponse().getContentAsString()).get("id").asText();

        MvcResult streamResult = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, answerId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceStream)
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();

        String body = streamResult.getResponse().getContentAsString();
        int safeIndex = body.indexOf("event:safe_response");
        int doneIndex = body.indexOf("event:done");

        assertThat(safeIndex).isGreaterThanOrEqualTo(0);
        assertThat(doneIndex).isGreaterThan(safeIndex);
    }

    @Test
    void shouldReturn403WhenAdminRoleCallsAgentOnlyBootstrap() throws Exception {
        String adminAccessToken = login("admin1", "admin1-pass", "55555555-5555-4555-8555-555555555555");

        mockMvc.perform(get("/v1/chat/bootstrap")
                .header("Authorization", "Bearer " + adminAccessToken)
                .header("X-Trace-Id", "66666666-6666-4666-8666-666666666666")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
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

        JsonNode jsonNode = objectMapper.readTree(result.getResponse().getContentAsString());
        return jsonNode.get("access_token").asText();
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

        JsonNode jsonNode = objectMapper.readTree(result.getResponse().getContentAsString());
        return jsonNode.get("session_id").asText();
    }
}
