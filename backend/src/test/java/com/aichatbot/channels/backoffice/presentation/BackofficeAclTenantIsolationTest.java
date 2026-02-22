package com.aichatbot.channels.backoffice.presentation;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0",
    "app.auth.mfa-enforce-ops-admin=false"
})
@AutoConfigureMockMvc
class BackofficeAclTenantIsolationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldRejectRbacAdminEndpointForOpsRole() throws Exception {
        String opsToken = login("ops1", "ops1-pass", "94000000-0000-4000-8000-000000000001")
            .get("access_token")
            .asText();

        mockMvc.perform(get("/v1/admin/rbac/approval-requests")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "94000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
    }

    @Test
    void shouldRejectCrossTenantDashboardQuery() throws Exception {
        String opsToken = login("ops1", "ops1-pass", "94000000-0000-4000-8000-000000000003")
            .get("access_token")
            .asText();

        mockMvc.perform(get("/v1/admin/dashboard/summary")
                .queryParam("tenant_id", "81000000-0000-4000-8000-000000000099")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "94000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"))
            .andExpect(jsonPath("$.trace_id").isNotEmpty());
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
