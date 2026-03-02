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
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0",
    "app.auth.mfa-enforce-ops-admin=false"
})
@AutoConfigureMockMvc
class AdminModelRoutingProviderContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldHandleModelRoutingProviderLifecycle() throws Exception {
        String adminToken = login("admin1", "admin1-pass", "c1000000-0000-4000-8000-000000000001")
            .get("access_token")
            .asText();
        String opsToken = login("ops1", "ops1-pass", "c1000000-0000-4000-8000-000000000002")
            .get("access_token")
            .asText();

        MvcResult createModelResult = mockMvc.perform(post("/v1/admin/models")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "provider":"ollama",
                      "model_name":"qwen2.5:3b-instruct"
                    }
                    """))
            .andExpect(status().isCreated())
            .andReturn();
        String modelId = objectMapper.readTree(createModelResult.getResponse().getContentAsString())
            .get("resource_key")
            .asText();

        mockMvc.perform(get("/v1/admin/models")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(post("/v1/admin/models/{model_id}/activate", modelId)
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000005")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ACTIVE"));

        mockMvc.perform(post("/v1/admin/models/{model_id}/rollback", modelId)
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000006")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ROLLED_BACK"));

        mockMvc.perform(put("/v1/admin/routing-rules/{rule_id}", "default-rule")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000007")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "provider":"ollama",
                      "weight":100
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resource_key").value("default-rule"));

        mockMvc.perform(post("/v1/admin/routing-rules/test")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000008")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "rule_id":"default-rule",
                      "prompt":"route this request"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("MATCHED"));

        mockMvc.perform(put("/v1/admin/provider-keys/{provider}", "ollama")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000009")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "secret_ref":"secret://ollama/main"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resource_key").value("ollama"));

        mockMvc.perform(post("/v1/admin/provider-keys/{provider}/rotate", "ollama")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000010")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ROTATED"));

        mockMvc.perform(post("/v1/admin/providers/{provider_id}/secret-ref", "ollama")
                .header("Authorization", "Bearer " + adminToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000011")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "secret_ref":"secret://ollama/provider"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resource_key").value("ollama"));

        mockMvc.perform(get("/v1/ops/llm/providers/health")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000012")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(post("/v1/ops/llm/providers/{provider}/kill-switch", "ollama")
                .header("Authorization", "Bearer " + opsToken)
                .header("X-Trace-Id", "c1000000-0000-4000-8000-000000000013")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "enabled": true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("KILL_SWITCH_ON"));
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
