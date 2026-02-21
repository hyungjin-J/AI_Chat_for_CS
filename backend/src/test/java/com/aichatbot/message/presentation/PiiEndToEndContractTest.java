package com.aichatbot.message.presentation;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aichatbot.llm.application.LlmService;
import com.aichatbot.message.application.MessageView;
import com.aichatbot.message.infrastructure.MessageRepository;
import com.aichatbot.rag.application.CitationView;
import com.aichatbot.rag.infrastructure.CitationRepository;
import com.aichatbot.rag.infrastructure.RagSearchLogRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
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
class PiiEndToEndContractTest {

    private static final Pattern CHUNK_ID_PATTERN = Pattern.compile("chunk_id=([0-9a-fA-F\\-]{36})");
    private static final Pattern RAW_EMAIL = Pattern.compile("sample\\.user\\+demo@testmail\\.local", Pattern.CASE_INSENSITIVE);
    private static final Pattern RAW_PHONE = Pattern.compile("010-1234-5678");
    private static final Pattern RAW_ORDER = Pattern.compile("ORD-99887766");
    private static final Pattern RAW_ADDRESS = Pattern.compile("SampleCity TestRoad 123", Pattern.CASE_INSENSITIVE);

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private MessageRepository messageRepository;

    @Autowired
    private RagSearchLogRepository ragSearchLogRepository;

    @Autowired
    private CitationRepository citationRepository;

    @SpyBean
    private LlmService llmService;

    @AfterEach
    void tearDown() {
        reset(llmService);
    }

    @Test
    void shouldMaskPiiInPromptLogAndPersistence() throws Exception {
        AtomicReference<String> promptCapture = new AtomicReference<>();
        doAnswer(invocation -> {
            String prompt = invocation.getArgument(0, String.class);
            String messageId = invocation.getArgument(1, String.class);
            promptCapture.set(prompt);

            String chunkId = extractChunkId(prompt);
            return """
                {
                  "schema_version":"v1",
                  "response_type":"answer",
                  "answer":{"text":"정상 응답"},
                  "citations":[
                    {
                      "citation_id":"c1",
                      "message_id":"%s",
                      "chunk_id":"%s",
                      "rank_no":1,
                      "excerpt_masked":"문의 채널은 ***@*** 입니다."
                    }
                  ],
                  "evidence":{"score":0.95,"threshold":0.7}
                }
                """.formatted(messageId, chunkId);
        }).when(llmService).generateAnswerContractJson(anyString(), anyString());

        Logger rootLogger = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        rootLogger.addAppender(appender);

        try {
            String loginTrace = "40000000-0000-4000-8000-000000000000";
            LoginPrincipal principal = login("agent1", "agent1-pass", loginTrace);
            String sessionTrace = "40000000-0000-4000-8000-000000000001";
            String sessionId = createSession(principal.accessToken(), sessionTrace);

            String piiInput = "refund policy request. contact sample.user+demo@testmail.local, phone 010-1234-5678, "
                + "address SampleCity TestRoad 123, order ORD-99887766";
            String postTrace = "40000000-0000-4000-8000-000000000002";
            String answerMessageId = postMessage(principal.accessToken(), sessionId, piiInput, postTrace);
            String streamTrace = "40000000-0000-4000-8000-000000000003";
            String streamBody = stream(principal.accessToken(), sessionId, answerMessageId, streamTrace);

            String capturedPrompt = promptCapture.get();
            assertThat(capturedPrompt).isNotBlank();
            assertNoRawPii(capturedPrompt);

            String tenantId = principal.tenantId();
            List<MessageView> messages = messageRepository.findByConversation(
                UUID.fromString(tenantId),
                UUID.fromString(sessionId)
            );
            assertThat(messages).isNotEmpty();
            messages.forEach(message -> assertNoRawPii(message.messageText()));

            String maskedQuery = ragSearchLogRepository.findLatestMaskedQueryByConversation(
                UUID.fromString(tenantId),
                UUID.fromString(sessionId)
            );
            assertThat(maskedQuery).isNotBlank();
            assertNoRawPii(maskedQuery);

            List<CitationView> citations = citationRepository.findByMessageId(
                UUID.fromString(tenantId),
                UUID.fromString(answerMessageId),
                null,
                10
            );
            assertThat(citations).isNotEmpty();
            citations.forEach(citation -> assertNoRawPii(citation.excerptMasked()));

            String combinedLogs = appender.list.stream()
                .map(ILoggingEvent::getFormattedMessage)
                .reduce("", (left, right) -> left + "\n" + right);
            assertNoRawPii(combinedLogs);
            assertNoRawPii(streamBody);
            assertThat(streamBody).contains("event:done");

            for (SseEvent event : parseEvents(streamBody)) {
                JsonNode payload = parsePayload(event.data());
                if ("token".equals(event.event())) {
                    assertNoRawPii(payload.path("text").asText());
                } else if ("citation".equals(event.event())) {
                    assertNoRawPii(payload.path("excerpt_masked").asText());
                } else {
                    assertNoRawPii(payload.toString());
                }
            }
        } finally {
            rootLogger.detachAppender(appender);
            appender.stop();
        }
    }

    private void assertNoRawPii(String text) {
        String safe = text == null ? "" : text;
        assertThat(RAW_EMAIL.matcher(safe).find()).isFalse();
        assertThat(RAW_PHONE.matcher(safe).find()).isFalse();
        assertThat(RAW_ORDER.matcher(safe).find()).isFalse();
        assertThat(RAW_ADDRESS.matcher(safe).find()).isFalse();
    }

    private String extractChunkId(String prompt) {
        Matcher matcher = CHUNK_ID_PATTERN.matcher(prompt == null ? "" : prompt);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return "30000000-0000-0000-0000-000000000005";
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

    private JsonNode parsePayload(String rawData) throws Exception {
        JsonNode node = objectMapper.readTree(rawData);
        if (node.isTextual()) {
            return objectMapper.readTree(node.asText());
        }
        return node;
    }

    private record SseEvent(String event, String data) {
    }

    private record LoginPrincipal(String accessToken, String tenantId) {
    }
}
