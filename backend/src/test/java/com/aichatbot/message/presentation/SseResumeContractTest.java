package com.aichatbot.message.presentation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
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
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0"
})
@AutoConfigureMockMvc
class SseResumeContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldReplayOnlyEventsAfterLastEventId() throws Exception {
        String accessToken = login("agent1", "agent1-pass", "81000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "81000000-0000-4000-8000-000000000001");
        String answerId = postMessage(accessToken, sessionId, "refund policy", "81000000-0000-4000-8000-000000000002");

        String baselineBody = stream(accessToken, sessionId, answerId, "81000000-0000-4000-8000-000000000003", null);
        List<Integer> baselineIds = parseEventIds(baselineBody);
        assertThat(baselineIds).isNotEmpty();
        assertThat(baselineBody).contains("event:done");

        int checkpoint = baselineIds.stream()
            .filter(id -> id > 0)
            .findFirst()
            .orElse(1);

        String resumedBody = stream(accessToken, sessionId, answerId, "81000000-0000-4000-8000-000000000004", checkpoint);
        List<Integer> resumedIds = parseEventIds(resumedBody);
        List<Integer> expected = baselineIds.stream()
            .filter(id -> id > checkpoint)
            .collect(Collectors.toList());

        assertThat(resumedIds).isEqualTo(expected);
        assertThat(resumedBody).contains("event:done");
    }

    private List<Integer> parseEventIds(String body) {
        List<Integer> ids = new ArrayList<>();
        for (String line : body.split("\\R")) {
            String trimmed = line.trim();
            if (!trimmed.startsWith("id:")) {
                continue;
            }
            String raw = trimmed.substring(3).trim();
            try {
                ids.add(Integer.parseInt(raw));
            } catch (NumberFormatException ignored) {
            }
        }
        return ids;
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
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("session_id").asText();
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
                      "top_k":3,
                      "client_nonce":"nonce-message"
                    }
                    """.formatted(text)))
            .andExpect(status().isAccepted())
            .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asText();
    }

    private String stream(String accessToken, String sessionId, String messageId, String traceId, Integer lastEventId) throws Exception {
        if (lastEventId == null) {
            MvcResult result = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, messageId)
                    .header("Authorization", "Bearer " + accessToken)
                    .header("X-Trace-Id", traceId)
                    .header("X-Tenant-Key", "demo-tenant"))
                .andExpect(status().isOk())
                .andReturn();
            return result.getResponse().getContentAsString();
        }

        MvcResult result = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream/resume", sessionId, messageId)
                .queryParam("last_event_id", String.valueOf(lastEventId))
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();
        return result.getResponse().getContentAsString();
    }
}
