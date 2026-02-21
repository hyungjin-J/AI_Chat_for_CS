package com.aichatbot.auth.presentation;

import com.aichatbot.auth.infrastructure.AuthRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0"
})
@AutoConfigureMockMvc
class AuthHardeningContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AuthRepository authRepository;

    @AfterEach
    void resetLockoutState() {
        authRepository.findActiveUserByTenantAndLoginId("demo-tenant", "agent1")
            .ifPresent(user -> authRepository.resetFailedLogin(user.userId()));
        authRepository.findActiveUserByTenantAndLoginId("demo-tenant", "admin1")
            .ifPresent(user -> authRepository.resetFailedLogin(user.userId()));
        authRepository.findActiveUserByTenantAndLoginId("demo-tenant", "ops1")
            .ifPresent(user -> authRepository.resetFailedLogin(user.userId()));
    }

    @Test
    void shouldReturn401AuthStalePermissionWhenPermissionVersionChanges() throws Exception {
        String agentToken = login("agent1", "agent1-pass", "81000000-0000-4000-8000-000000000001").get("access_token").asText();
        String adminToken = login("admin1", "admin1-pass", "81000000-0000-4000-8000-000000000002").get("access_token").asText();
        String admin2Token = login("admin2", "admin2-pass", "81000000-0000-4000-8000-000000000005").get("access_token").asText();
        String admin3Token = login("admin3", "admin3-pass", "81000000-0000-4000-8000-000000000006").get("access_token").asText();

        MvcResult createRequestResult = mockMvc.perform(put("/v1/admin/rbac/matrix/admin.dashboard.summary")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "81000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "role_code":"OPS",
                      "admin_level":"MANAGER",
                      "allowed":true,
                      "reason":"stale-permission-test"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("pending"))
            .andReturn();
        String requestId = objectMapper.readTree(createRequestResult.getResponse().getContentAsString())
            .get("request_id")
            .asText();

        mockMvc.perform(post("/v1/admin/rbac/approval-requests/{request_id}/approve", requestId)
                .header("Authorization", "Bearer " + admin2Token)
                .header("X-Trace-Id", "81000000-0000-4000-8000-000000000007")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "comment":"approve-1"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("PENDING"));

        mockMvc.perform(post("/v1/admin/rbac/approval-requests/{request_id}/approve", requestId)
                .header("Authorization", "Bearer " + admin3Token)
                .header("X-Trace-Id", "81000000-0000-4000-8000-000000000008")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "comment":"approve-2"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("APPLIED"));

        mockMvc.perform(get("/v1/chat/bootstrap")
                .header("Authorization", "Bearer " + agentToken)
                .header("X-Trace-Id", "81000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.error_code").value("AUTH_STALE_PERMISSION"));
    }

    @Test
    void shouldDetectRefreshReuseAndReturn409() throws Exception {
        JsonNode loginJson = login("ops1", "ops1-pass", "82000000-0000-4000-8000-000000000001");
        String oldRefresh = loginJson.get("refresh_token").asText();

        JsonNode refreshed = refresh(oldRefresh, "82000000-0000-4000-8000-000000000002");
        assertThat(refreshed.get("access_token").asText()).isNotBlank();

        mockMvc.perform(post("/v1/auth/refresh")
                .header("X-Trace-Id", "82000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-refresh-reuse")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "refresh_token":"%s",
                      "client_type":"web",
                      "client_nonce":"reuse-check"
                    }
                    """.formatted(oldRefresh)))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.error_code").value("AUTH_REFRESH_REUSE_DETECTED"));
    }

    @Test
    void shouldLockAccountAfterThresholdAndReturnRetryAfterHeader() throws Exception {
        for (int attempt = 1; attempt <= 4; attempt++) {
            mockMvc.perform(post("/v1/auth/login")
                    .header("X-Trace-Id", "83000000-0000-4000-8000-00000000000" + attempt)
                    .header("X-Tenant-Key", "demo-tenant")
                    .header("Idempotency-Key", "idem-lock-" + attempt)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                        {
                          "login_id":"agent1",
                          "password":"wrong-pass",
                          "client_type":"web",
                          "client_nonce":"nonce-lock-%d"
                        }
                        """.formatted(attempt)))
                .andExpect(status().isUnauthorized());
        }

        mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", "83000000-0000-4000-8000-000000000009")
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-lock-5")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "login_id":"agent1",
                      "password":"wrong-pass",
                      "client_type":"web",
                      "client_nonce":"nonce-lock-5"
                    }
                    """))
            .andExpect(status().isTooManyRequests())
            .andExpect(jsonPath("$.error_code").value("AUTH_LOCKED"))
            .andExpect(header().exists("Retry-After"));
    }

    private JsonNode refresh(String refreshToken, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/auth/refresh")
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-refresh-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "refresh_token":"%s",
                      "client_type":"web",
                      "client_nonce":"nonce-refresh"
                    }
                    """.formatted(refreshToken)))
            .andExpect(status().isCreated())
            .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode login(String loginId, String password, String traceId) throws Exception {
        MvcResult result = mockMvc.perform(post("/v1/auth/login")
                .header("X-Trace-Id", traceId)
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-" + loginId + "-" + traceId)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "login_id":"%s",
                      "password":"%s",
                      "client_type":"web",
                      "client_nonce":"nonce-login"
                    }
                    """.formatted(loginId, password)))
            .andExpect(status().isCreated())
            .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }
}
