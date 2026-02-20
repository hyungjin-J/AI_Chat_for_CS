package com.aichatbot.global.observability;

import com.aichatbot.llm.application.LlmService;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
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
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.trace.require-header=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.7"
})
@AutoConfigureMockMvc
class TraceIdContractTest {

    private static final Pattern UUID_PATTERN = Pattern.compile(
        "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
    );

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MessageRepository messageRepository;

    @SpyBean
    private LlmService llmService;

    @AfterEach
    void tearDown() {
        reset(llmService);
    }

    @Test
    void shouldGenerateTraceIdWhenHeaderMissing() throws Exception {
        MvcResult result = mockMvc.perform(get("/health"))
            .andExpect(status().isOk())
            .andExpect(header().exists("X-Trace-Id"))
            .andReturn();

        String traceId = result.getResponse().getHeader("X-Trace-Id");
        JsonNode body = objectMapper.readTree(result.getResponse().getContentAsString());

        assertThat(traceId).isNotBlank();
        assertThat(UUID_PATTERN.matcher(traceId).matches()).isTrue();
        assertThat(body.get("trace_id").asText()).isEqualTo(traceId);
    }

    @Test
    void shouldReturn409WhenTraceIdFormatInvalid() throws Exception {
        mockMvc.perform(get("/health")
                .header("X-Trace-Id", "not-a-uuid"))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.error_code").value("SYS-004-409-TRACE"))
            .andExpect(jsonPath("$.details[0]").value("invalid_trace_id_format"));
    }

    @Test
    void shouldPropagateSameTraceIdToSseErrorAndDoneEvents() throws Exception {
        doReturn("""
            {
              "schema_version":"v1",
              "response_type":"answer",
              "answer":{"text":"broken"}
            """
        ).when(llmService).generateAnswerContractJson(anyString(), anyString());
        doAnswer(invocation -> invocation.getArgument(0, String.class))
            .when(llmService).repairAnswerContractJson(anyString(), anyString(), anyString());

        LoginPrincipal principal = login("agent1", "agent1-pass", "50000000-0000-4000-8000-000000000000");
        String sessionId = createSession(principal.accessToken(), "50000000-0000-4000-8000-000000000001");
        String traceId = "50000000-0000-4000-8000-000000000002";

        MvcResult messageResult = mockMvc.perform(post("/v1/sessions/{session_id}/messages", sessionId)
                .header("Authorization", "Bearer " + principal.accessToken())
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-message-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "text":"refund policy",
                      "top_k":3,
                      "client_nonce":"nonce-message"
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.trace_id").value(traceId))
            .andReturn();

        String messageId = objectMapper.readTree(messageResult.getResponse().getContentAsString()).get("id").asText();
        String streamBody = stream(principal.accessToken(), sessionId, messageId, traceId);

        JsonNode errorPayload = firstEventPayload(streamBody, "error");
        JsonNode donePayload = firstEventPayload(streamBody, "done");
        assertThat(errorPayload.path("trace_id").asText()).isEqualTo(traceId);
        assertThat(donePayload.path("trace_id").asText()).isEqualTo(traceId);
    }

    @Test
    void shouldPersistTraceIdInMessageRows() throws Exception {
        LoginPrincipal principal = login("agent1", "agent1-pass", "60000000-0000-4000-8000-000000000000");
        String sessionId = createSession(principal.accessToken(), "60000000-0000-4000-8000-000000000001");
        String traceId = "60000000-0000-4000-8000-000000000002";

        postMessage(principal.accessToken(), sessionId, "refund policy", traceId);

        List<MessageView> messages = messageRepository.findByConversation(
            UUID.fromString(principal.tenantId()),
            UUID.fromString(sessionId)
        );
        assertThat(messages).isNotEmpty();
        assertThat(messages).allMatch(message -> traceId.equals(message.traceId()));
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

    private LoginPrincipal login(String loginId, String password, String traceId) throws Exception {
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
        return new LoginPrincipal(json.get("access_token").asText(), json.get("tenant_id").asText());
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

    private record LoginPrincipal(String accessToken, String tenantId) {
    }
}
