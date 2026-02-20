package com.aichatbot.message.presentation;

import com.aichatbot.llm.application.LlmService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.reset;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.7"
})
@AutoConfigureMockMvc
class MessageAnswerContractNegativeFlowTest {

    private static final Pattern CHUNK_ID_PATTERN = Pattern.compile("chunk_id=([0-9a-fA-F\\-]{36})");

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @SpyBean
    private LlmService llmService;

    @AfterEach
    void tearDown() {
        reset(llmService);
    }

    @Test
    void shouldFailClosedWhenCitationsMissing() throws Exception {
        doReturn("""
            {
              "schema_version":"v1",
              "response_type":"answer",
              "answer":{"text":"근거가 없는 답변"},
              "citations":[],
              "evidence":{"score":0.95,"threshold":0.7}
            }
            """).when(llmService).generateAnswerContractJson(anyString(), anyString());
        doAnswer(invocation -> invocation.getArgument(0, String.class))
            .when(llmService).repairAnswerContractJson(anyString(), anyString(), anyString());

        String traceId = "10000000-0000-4000-8000-000000000001";
        String accessToken = login("agent1", "agent1-pass", "10000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "10000000-0000-4000-8000-000000000002");
        String answerId = postMessage(accessToken, sessionId, "refund policy", traceId);
        String streamBody = stream(accessToken, sessionId, answerId, traceId);

        assertSafeResponse(streamBody);
        assertNoTokenEvent(streamBody);

        JsonNode errorPayload = firstEventPayload(streamBody, "error");
        assertThat(errorPayload.path("error_code").asText()).isEqualTo("AI-009-409-CITATION");
        assertThat(errorPayload.path("trace_id").asText()).isEqualTo(traceId);
    }

    @Test
    void shouldFailClosedWhenSchemaInvalid() throws Exception {
        doReturn("""
            {
              "schema_version":"v1",
              "response_type":"answer",
              "answer":{"text":"broken"}
            """
        ).when(llmService).generateAnswerContractJson(anyString(), anyString());
        doAnswer(invocation -> invocation.getArgument(0, String.class))
            .when(llmService).repairAnswerContractJson(anyString(), anyString(), anyString());

        String traceId = "20000000-0000-4000-8000-000000000001";
        String accessToken = login("agent1", "agent1-pass", "20000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "20000000-0000-4000-8000-000000000002");
        String answerId = postMessage(accessToken, sessionId, "refund policy", traceId);
        String streamBody = stream(accessToken, sessionId, answerId, traceId);

        assertSafeResponse(streamBody);
        assertNoTokenEvent(streamBody);

        JsonNode errorPayload = firstEventPayload(streamBody, "error");
        assertThat(errorPayload.path("error_code").asText()).isEqualTo("AI-009-422-SCHEMA");
        assertThat(errorPayload.path("trace_id").asText()).isEqualTo(traceId);
    }

    @Test
    void shouldFailClosedWhenEvidenceBelowThreshold() throws Exception {
        doAnswer(invocation -> {
            String prompt = invocation.getArgument(0, String.class);
            String messageId = invocation.getArgument(1, String.class);
            String chunkId = extractChunkId(prompt);
            return """
                {
                  "schema_version":"v1",
                  "response_type":"answer",
                  "answer":{"text":"근거 점수 부족"},
                  "citations":[
                    {
                      "citation_id":"c1",
                      "message_id":"%s",
                      "chunk_id":"%s",
                      "rank_no":1,
                      "excerpt_masked":"근거 발췌"
                    }
                  ],
                  "evidence":{"score":0.1,"threshold":0.9}
                }
                """.formatted(messageId, chunkId);
        }).when(llmService).generateAnswerContractJson(anyString(), anyString());
        doAnswer(invocation -> invocation.getArgument(0, String.class))
            .when(llmService).repairAnswerContractJson(anyString(), anyString(), anyString());

        String traceId = "30000000-0000-4000-8000-000000000001";
        String accessToken = login("agent1", "agent1-pass", "30000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "30000000-0000-4000-8000-000000000002");
        String answerId = postMessage(accessToken, sessionId, "refund policy", traceId);
        String streamBody = stream(accessToken, sessionId, answerId, traceId);

        assertSafeResponse(streamBody);
        assertNoTokenEvent(streamBody);

        JsonNode errorPayload = firstEventPayload(streamBody, "error");
        assertThat(errorPayload.path("error_code").asText()).isEqualTo("AI-009-409-EVIDENCE");
        assertThat(errorPayload.path("trace_id").asText()).isEqualTo(traceId);
    }

    private void assertSafeResponse(String body) {
        int safeIndex = body.indexOf("event:safe_response");
        int errorIndex = body.indexOf("event:error");
        int doneIndex = body.indexOf("event:done");

        assertThat(safeIndex).isGreaterThanOrEqualTo(0);
        assertThat(errorIndex).isGreaterThan(safeIndex);
        assertThat(doneIndex).isGreaterThan(errorIndex);
    }

    private void assertNoTokenEvent(String body) {
        assertThat(body).doesNotContain("event:token");
    }

    private JsonNode firstEventPayload(String body, String eventName) throws Exception {
        for (SseEvent event : parseEvents(body)) {
            if (eventName.equals(event.event())) {
                JsonNode parsed = objectMapper.readTree(event.data());
                if (parsed.isTextual()) {
                    return objectMapper.readTree(parsed.asText());
                }
                return parsed;
            }
        }
        throw new IllegalStateException("missing_event:" + eventName);
    }

    private List<SseEvent> parseEvents(String body) {
        List<SseEvent> events = new ArrayList<>();
        String currentEvent = null;
        StringBuilder currentData = new StringBuilder();

        for (String rawLine : body.split("\\R")) {
            String line = rawLine.trim();
            if (line.startsWith("event:")) {
                currentEvent = line.substring("event:".length()).trim();
            } else if (line.startsWith("data:")) {
                if (currentData.length() > 0) {
                    currentData.append('\n');
                }
                currentData.append(line.substring("data:".length()).trim());
            } else if (line.isEmpty()) {
                if (currentEvent != null && currentData.length() > 0) {
                    events.add(new SseEvent(currentEvent, currentData.toString()));
                }
                currentEvent = null;
                currentData = new StringBuilder();
            }
        }

        if (currentEvent != null && currentData.length() > 0) {
            events.add(new SseEvent(currentEvent, currentData.toString()));
        }
        return events;
    }

    private String extractChunkId(String prompt) {
        Matcher matcher = CHUNK_ID_PATTERN.matcher(prompt == null ? "" : prompt);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return "30000000-0000-0000-0000-000000000005";
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
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("access_token").asText();
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

    private String stream(String accessToken, String sessionId, String messageId, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, messageId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();
        return result.getResponse().getContentAsString();
    }

    private record SseEvent(String event, String data) {
    }
}
