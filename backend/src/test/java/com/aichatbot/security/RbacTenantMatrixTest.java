package com.aichatbot.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.stream.Stream;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

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
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class RbacTenantMatrixTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @ParameterizedTest(name = "{0}")
    @MethodSource("noAuthCases")
    void shouldReturn401WhenAuthenticationMissing(String label, MockHttpServletRequestBuilder request) throws Exception {
        mockMvc.perform(request)
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.error_code").value("SEC-001-401"));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("wrongRoleCases")
    void shouldReturn403WhenRoleIsInsufficient(String label, MockHttpServletRequestBuilder request) throws Exception {
        mockMvc.perform(request)
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("crossTenantCases")
    void shouldRejectCrossTenantJwtRequests(String label, MockHttpServletRequestBuilder request) throws Exception {
        mockMvc.perform(request)
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SYS-002-403"))
            .andExpect(jsonPath("$.details[0]").value("tenant_mismatch"));
    }

    private static Stream<Arguments> noAuthCases() {
        return Stream.of(
            Arguments.of(
                "sessions:create",
                post("/v1/sessions")
                    .header("X-Trace-Id", "71000000-0000-4000-8000-000000000001")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-noauth-session")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{}")
            ),
            Arguments.of(
                "messages:create",
                post("/v1/sessions/{session_id}/messages", "71000000-0000-4000-8000-000000000011")
                    .header("X-Trace-Id", "71000000-0000-4000-8000-000000000002")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-noauth-message")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "text":"hello",
                          "top_k":1,
                          "client_nonce":"nonce-a"
                        }
                        """)
            ),
            Arguments.of(
                "stream:get",
                get("/v1/sessions/{session_id}/messages/{message_id}/stream",
                    "71000000-0000-4000-8000-000000000012",
                    "71000000-0000-4000-8000-000000000013")
                    .header("X-Trace-Id", "71000000-0000-4000-8000-000000000003")
                    .header("X-Tenant-Key", "demo-tenant")
            ),
            Arguments.of(
                "rag:retrieve",
                post("/v1/rag/retrieve")
                    .header("X-Trace-Id", "71000000-0000-4000-8000-000000000004")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-noauth-rag")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "query":"refund policy",
                          "top_k":1
                        }
                        """)
            ),
            Arguments.of(
                "admin:usage-report",
                get("/v1/admin/tenants/{tenant_id}/usage-report", "demo-tenant")
                    .header("X-Trace-Id", "71000000-0000-4000-8000-000000000005")
                    .header("X-Tenant-Key", "demo-tenant")
            )
        );
    }

    private static Stream<Arguments> wrongRoleCases() {
        return Stream.of(
            Arguments.of(
                "sessions:create wrong role",
                post("/v1/sessions")
                    .header("X-Trace-Id", "72000000-0000-4000-8000-000000000001")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-wrong-session")
                    .header("X-User-Role", "ADMIN")
                    .header("X-User-Id", "wrong-role-admin")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{}")
            ),
            Arguments.of(
                "messages:create wrong role",
                post("/v1/sessions/{session_id}/messages", "72000000-0000-4000-8000-000000000011")
                    .header("X-Trace-Id", "72000000-0000-4000-8000-000000000002")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-wrong-message")
                    .header("X-User-Role", "ADMIN")
                    .header("X-User-Id", "wrong-role-admin")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "text":"hello",
                          "top_k":1,
                          "client_nonce":"nonce-b"
                        }
                        """)
            ),
            Arguments.of(
                "stream:get wrong role",
                get("/v1/sessions/{session_id}/messages/{message_id}/stream",
                    "72000000-0000-4000-8000-000000000012",
                    "72000000-0000-4000-8000-000000000013")
                    .header("X-Trace-Id", "72000000-0000-4000-8000-000000000003")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("X-User-Role", "ADMIN")
                    .header("X-User-Id", "wrong-role-admin")
            ),
            Arguments.of(
                "rag:retrieve wrong role",
                post("/v1/rag/retrieve")
                    .header("X-Trace-Id", "72000000-0000-4000-8000-000000000004")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-wrong-rag")
                    .header("X-User-Role", "AGENT")
                    .header("X-User-Id", "wrong-role-agent")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "query":"refund policy",
                          "top_k":1
                        }
                        """)
            ),
            Arguments.of(
                "admin:usage-report wrong role",
                get("/v1/admin/tenants/{tenant_id}/usage-report", "demo-tenant")
                    .header("X-Trace-Id", "72000000-0000-4000-8000-000000000005")
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("X-User-Role", "AGENT")
                    .header("X-User-Id", "wrong-role-agent")
            )
        );
    }

    private Stream<Arguments> crossTenantCases() throws Exception {
        AuthToken agent = login("agent1", "agent1-pass", "73000000-0000-4000-8000-000000000000");
        AuthToken admin = login("admin1", "admin1-pass", "73000000-0000-4000-8000-000000000001");
        String sessionId = createSession(agent.accessToken(), "73000000-0000-4000-8000-000000000002");
        String messageId = postMessage(agent.accessToken(), sessionId, "refund policy", "73000000-0000-4000-8000-000000000003");

        return Stream.of(
            Arguments.of(
                "sessions:create cross tenant",
                post("/v1/sessions")
                    .header("Authorization", "Bearer " + agent.accessToken())
                    .header("X-Trace-Id", "73000000-0000-4000-8000-000000000004")
                    .header("X-Tenant-Key", "tenant-a")
                    .header("Idempotency-Key", "idem-cross-session")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("{}")
            ),
            Arguments.of(
                "messages:create cross tenant",
                post("/v1/sessions/{session_id}/messages", sessionId)
                    .header("Authorization", "Bearer " + agent.accessToken())
                    .header("X-Trace-Id", "73000000-0000-4000-8000-000000000005")
                    .header("X-Tenant-Key", "tenant-a")
                    .header("Idempotency-Key", "idem-cross-message")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "text":"refund policy",
                          "top_k":1,
                          "client_nonce":"nonce-cross"
                        }
                        """)
            ),
            Arguments.of(
                "stream:get cross tenant",
                get("/v1/sessions/{session_id}/messages/{message_id}/stream", sessionId, messageId)
                    .header("Authorization", "Bearer " + agent.accessToken())
                    .header("X-Trace-Id", "73000000-0000-4000-8000-000000000006")
                    .header("X-Tenant-Key", "tenant-a")
            ),
            Arguments.of(
                "admin:usage-report cross tenant",
                get("/v1/admin/tenants/{tenant_id}/usage-report", "tenant-a")
                    .header("Authorization", "Bearer " + admin.accessToken())
                    .header("X-Trace-Id", "73000000-0000-4000-8000-000000000007")
                    .header("X-Tenant-Key", "tenant-a")
            )
        );
    }

    private AuthToken login(String loginId, String password, String traceId) throws Exception {
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
        return new AuthToken(json.get("access_token").asText());
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
                      "top_k":1,
                      "client_nonce":"nonce-message"
                    }
                    """.formatted(text)))
            .andExpect(status().isAccepted())
            .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asText();
    }

    private record AuthToken(String accessToken) {
    }
}
