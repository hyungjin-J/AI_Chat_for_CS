package com.aichatbot.contexts.conversation.session.presentation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0"
})
@AutoConfigureMockMvc
class SessionActionContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldCloseSessionWithAcceptedContract() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "71000000-0000-4000-8000-000000000001");
        String sessionId = createSession(accessToken, "71000000-0000-4000-8000-000000000002");

        mockMvc.perform(post("/v1/sessions/{session_id}/close", sessionId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "71000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "reason":"user_finished"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("accepted"))
            .andExpect(jsonPath("$.action").value("session_close"))
            .andExpect(jsonPath("$.session_id").value(sessionId))
            .andExpect(jsonPath("$.trace_id").value("71000000-0000-4000-8000-000000000003"));
    }

    @Test
    void shouldRetryMessageWithAcceptedContract() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "72000000-0000-4000-8000-000000000001");
        String sessionId = createSession(accessToken, "72000000-0000-4000-8000-000000000002");
        String messageId = postMessage(accessToken, sessionId, "refund policy", "72000000-0000-4000-8000-000000000003");

        mockMvc.perform(post("/v1/sessions/{session_id}/messages/{message_id}/retry", sessionId, messageId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "72000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "reason":"network_timeout"
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.result").value("accepted"))
            .andExpect(jsonPath("$.action").value("message_retry"))
            .andExpect(jsonPath("$.session_id").value(sessionId))
            .andExpect(jsonPath("$.trace_id").value("72000000-0000-4000-8000-000000000004"));
    }

    @Test
    void shouldPostQuickReplyWithAcceptedContract() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "73000000-0000-4000-8000-000000000001");
        String sessionId = createSession(accessToken, "73000000-0000-4000-8000-000000000002");
        String quickReplyId = "73000000-0000-4000-8000-000000000099";

        mockMvc.perform(post("/v1/sessions/{session_id}/quick-replies/{quick_reply_id}", sessionId, quickReplyId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "73000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "text":"Thanks. We are checking now."
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("accepted"))
            .andExpect(jsonPath("$.action").value("quick_reply"))
            .andExpect(jsonPath("$.session_id").value(sessionId))
            .andExpect(jsonPath("$.trace_id").value("73000000-0000-4000-8000-000000000003"));
    }

    private String login(String loginId, String password, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-" + loginId + "-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "login_id":"%s",
                      "password":"%s",
                      "channel_id":"test",
                      "client_nonce":"nonce-login"
                    }
                    """.formatted(loginId, password)))
            .andExpect(status().isCreated())
            .andReturn();

        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());
        return body.get("access_token").asText();
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

        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());
        return body.get("session_id").asText();
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
                      "text":"%s",
                      "top_k":2,
                      "client_nonce":"nonce-message"
                    }
                    """.formatted(text)))
            .andExpect(status().isAccepted())
            .andReturn();

        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());
        return body.get("id").asText();
    }
}

