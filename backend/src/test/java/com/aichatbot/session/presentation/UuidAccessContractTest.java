package com.aichatbot.session.presentation;

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

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0"
})
@AutoConfigureMockMvc
class UuidAccessContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void invalidUuidShouldReturn422() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "10111111-1111-4111-8111-111111111111");

        mockMvc.perform(get("/v1/sessions/{session_id}", "abc")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "10222222-2222-4222-8222-222222222222")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.error_code").value("API-003-422"))
            .andExpect(jsonPath("$.details[0]").value("session_id_invalid"));
    }

    @Test
    void nonExistentUuidShouldReturn404() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "10333333-3333-4333-8333-333333333333");
        String missingSessionId = "10444444-4444-4444-8444-444444444444";

        mockMvc.perform(get("/v1/sessions/{session_id}", missingSessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "10555555-5555-4555-8555-555555555555")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.error_code").value("API-004-404"))
            .andExpect(jsonPath("$.details[0]").value("session_not_found"));
    }

    @Test
    void crossTenantSessionAndMessageAccessShouldReturn403() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "10666666-6666-4666-8666-666666666666");
        String sessionId = createSession(accessToken, "10777777-7777-4777-8777-777777777777");
        String answerMessageId = postMessage(
            accessToken,
            sessionId,
            "Please summarize the refund policy.",
            "10888888-8888-4888-8888-888888888888"
        );

        mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, answerMessageId)
                .header("X-User-Role", "AGENT")
                .header("X-User-Id", "tenant-a-agent")
                .header("X-Trace-Id", "10999999-9999-4999-8999-999999999999")
                .header("X-Tenant-Key", "tenant-a"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
    }

    @Test
    void validUuidShouldKeepHappyPath() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "10aaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
        String sessionId = createSession(accessToken, "10bbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");

        MvcResult result = mockMvc.perform(get("/v1/sessions/{session_id}", sessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "10cccccc-cccc-4ccc-8ccc-cccccccccccc")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();

        JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
        assertThat(json.get("session_id").asText()).isEqualTo(sessionId);
    }

    private String login(String loginId, String password, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-login-" + traceId)
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

    private String postMessage(String accessToken, String sessionId, String text, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/sessions/{session_id}/messages", sessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-message-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "text": "%s",
                      "top_k": 1,
                      "client_nonce": "nonce-message"
                    }
                    """.formatted(text)))
            .andExpect(status().isAccepted())
            .andReturn();

        JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
        return json.get("id").asText();
    }
}
