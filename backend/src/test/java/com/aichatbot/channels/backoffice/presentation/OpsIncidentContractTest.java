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
    "app.auth.mfa-enforce-ops-admin=false",
    "app.security.allow-header-auth=true"
})
@AutoConfigureMockMvc
class OpsIncidentContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldHandleOpsIncidentEndpoints() throws Exception {
        String adminToken = login("admin1", "admin1-pass", "d1000000-0000-4000-8000-000000000001")
            .get("access_token")
            .asText();
        String opsToken = login("ops1", "ops1-pass", "d1000000-0000-4000-8000-000000000002")
            .get("access_token")
            .asText();

        mockMvc.perform(post("/v1/internal/events/ingest")
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "SYSTEM")
                .header("X-User-Id", "system1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "event_type":"OPS_EVENT_INGEST_TEST",
                      "metric_key":"audit_export_requested",
                      "metric_value":1,
                      "dimensions":{"scope":"test"}
                    }
                    """))
            .andExpect(status().isAccepted());

        mockMvc.perform(get("/v1/ops/traces")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(get("/v1/ops/metrics/summary")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000005")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(post("/v1/ops/rollbacks")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000006")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "target_type":"MODEL",
                      "target_id":"fallback-model",
                      "reason":"manual rollback drill"
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.status").value("REQUESTED"));

        mockMvc.perform(get("/v1/ops/workflow/reports")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000007")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.recent_rollback_count").isNumber());

        mockMvc.perform(get("/v1/ops/mcp/servers/{server_id}/health", "notion")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000008")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("healthy"));

        mockMvc.perform(get("/v1/admin/version-bundles")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000009")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk());

        mockMvc.perform(post("/v1/admin/version-bundles/{bundle_id}/activate", "bundle-2026-03")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000010")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ACTIVE"));

        mockMvc.perform(post("/v1/admin/version-bundles/{bundle_id}/rollback", "bundle-2026-03")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "d1000000-0000-4000-8000-000000000011")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ROLLED_BACK"));
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
