package com.aichatbot.message.presentation;

import com.aichatbot.llm.application.LlmService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
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
import static org.mockito.Mockito.reset;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0",
    "app.budget.sse-concurrency-max-per-user=1",
    "app.budget.sse-hold-ms=1200"
})
@AutoConfigureMockMvc
class SseConcurrencyLimitContractTest {

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
    void shouldEnforceSseConcurrencyLimitAndReleaseAfterCompletion() throws Exception {
        stubValidAnswerContract();

        String accessToken = login("agent1", "agent1-pass", "91000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "91000000-0000-4000-8000-000000000001");
        String answerMessageId = postMessage(accessToken, sessionId, "refund policy", "91000000-0000-4000-8000-000000000002");

        ExecutorService executorService = Executors.newSingleThreadExecutor();
        Future<String> firstStream = executorService.submit(
            () -> stream(accessToken, sessionId, answerMessageId, "91000000-0000-4000-8000-000000000003")
        );

        // Why: Keep the first stream active long enough to prove server-side concurrency rejection.
        Thread.sleep(150L);

        mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, answerMessageId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "91000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isTooManyRequests())
            .andExpect(header().exists("Retry-After"))
            .andExpect(header().exists("X-RateLimit-Limit"))
            .andExpect(header().exists("X-RateLimit-Remaining"))
            .andExpect(header().exists("X-RateLimit-Reset"))
            .andExpect(jsonPath("$.error_code").value("API-008-429-SSE"))
            .andExpect(jsonPath("$.message").isString())
            .andExpect(jsonPath("$.trace_id").value("91000000-0000-4000-8000-000000000004"))
            .andExpect(jsonPath("$.details[0]").value("quota_exceeded"));

        String firstStreamBody;
        try {
            firstStreamBody = firstStream.get(10, TimeUnit.SECONDS);
        } finally {
            executorService.shutdownNow();
        }
        assertThat(firstStreamBody).contains("event:token");
        assertThat(firstStreamBody).contains("event:citation");
        assertThat(firstStreamBody).contains("event:done");

        String resumedAfterRelease = stream(
            accessToken,
            sessionId,
            answerMessageId,
            "91000000-0000-4000-8000-000000000005"
        );
        assertThat(resumedAfterRelease).contains("event:done");
    }

    @Test
    void shouldNotProduceFalse429AfterCompletedStreamFinallyRelease() throws Exception {
        stubValidAnswerContract();

        String accessToken = login("agent1", "agent1-pass", "92000000-0000-4000-8000-000000000000");
        String sessionId = createSession(accessToken, "92000000-0000-4000-8000-000000000001");
        String answerMessageId = postMessage(accessToken, sessionId, "refund policy", "92000000-0000-4000-8000-000000000002");

        String first = stream(accessToken, sessionId, answerMessageId, "92000000-0000-4000-8000-000000000003");
        assertThat(first).contains("event:done");

        // Why: This request is sequential, not concurrent. 429 here would indicate lock leakage.
        MvcResult secondResult = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, answerMessageId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "92000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();
        String second = secondResult.getResponse().getContentAsString();
        assertThat(second).contains("event:done");
        assertThat(second).doesNotContain("API-008-429-SSE");
    }

    private void stubValidAnswerContract() {
        doAnswer(invocation -> {
            String prompt = invocation.getArgument(0, String.class);
            String messageId = invocation.getArgument(1, String.class);
            String chunkId = extractChunkId(prompt);
            return """
                {
                  "schema_version":"v1",
                  "response_type":"answer",
                  "answer":{"text":"policy response for concurrency test"},
                  "citations":[
                    {
                      "citation_id":"c1",
                      "message_id":"%s",
                      "chunk_id":"%s",
                      "rank_no":1,
                      "excerpt_masked":"masked evidence"
                    }
                  ],
                  "evidence":{"score":0.95,"threshold":0.0}
                }
                """.formatted(messageId, chunkId);
        }).when(llmService).generateAnswerContractJson(anyString(), anyString());
        doAnswer(invocation -> invocation.getArgument(0, String.class))
            .when(llmService).repairAnswerContractJson(anyString(), anyString(), anyString());
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

    private String stream(String accessToken, String sessionId, String messageId, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, messageId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();
        return result.getResponse().getContentAsString();
    }
}
