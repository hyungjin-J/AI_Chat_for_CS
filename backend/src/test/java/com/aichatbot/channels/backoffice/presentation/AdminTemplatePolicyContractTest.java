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
class AdminTemplatePolicyContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldHandleTemplateAndPolicyLifecycle() throws Exception {
        String accessToken = login("admin1", "admin1-pass", "b1000000-0000-4000-8000-000000000001")
            .get("access_token")
            .asText();

        MvcResult createTemplateResult = mockMvc.perform(post("/v1/admin/templates")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "name":"refund_followup",
                      "body":"follow up template body"
                    }
                    """))
            .andExpect(status().isCreated())
            .andReturn();
        String templateId = objectMapper.readTree(createTemplateResult.getResponse().getContentAsString())
            .get("resource_key")
            .asText();

        mockMvc.perform(get("/v1/admin/templates")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(post("/v1/admin/templates/{template_id}/approve", templateId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("APPROVED"));

        mockMvc.perform(post("/v1/admin/templates/{template_id}/deploy", templateId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000005")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("DEPLOYED"));

        mockMvc.perform(post("/v1/admin/templates/{template_id}/rollback", templateId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000006")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ROLLED_BACK"));

        mockMvc.perform(put("/v1/admin/policies/{policy_id}", "answer_contract")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "b1000000-0000-4000-8000-000000000007")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "fail_closed": true,
                      "citation_required": true
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resource_key").value("answer_contract"));
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
