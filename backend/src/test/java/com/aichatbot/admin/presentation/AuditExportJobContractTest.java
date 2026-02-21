package com.aichatbot.admin.presentation;

import com.aichatbot.global.audit.AuditExportJobService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
    "spring.task.scheduling.enabled=false",
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.0",
    "app.auth.mfa-enforce-ops-admin=false"
})
@AutoConfigureMockMvc
class AuditExportJobContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AuditExportJobService auditExportJobService;

    @Test
    void shouldCreateProcessAndDownloadAuditExportJob() throws Exception {
        String accessToken = login("ops1", "ops1-pass", "91000000-0000-4000-8000-000000000001").get("access_token").asText();

        MvcResult createResult = mockMvc.perform(post("/v1/admin/audit-logs/export-jobs")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "91000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "format":"json",
                      "from_utc":"2026-03-01T00:00:00Z",
                      "to_utc":"2026-03-01T23:59:59Z",
                      "row_limit":200
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.status").value("PENDING"))
            .andReturn();

        String jobId = objectMapper.readTree(createResult.getResponse().getContentAsString()).get("job_id").asText();
        auditExportJobService.processPendingJobs(20);

        mockMvc.perform(get("/v1/admin/audit-logs/export-jobs/{job_id}", jobId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "91000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("DONE"));

        mockMvc.perform(get("/v1/admin/audit-logs/export-jobs/{job_id}/download", jobId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "91000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk());
    }

    @Test
    void shouldRejectDownloadWhenJobNotReady() throws Exception {
        String accessToken = login("ops1", "ops1-pass", "92000000-0000-4000-8000-000000000001").get("access_token").asText();

        MvcResult createResult = mockMvc.perform(post("/v1/admin/audit-logs/export-jobs")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "92000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "format":"csv",
                      "row_limit":100
                    }
                    """))
            .andExpect(status().isAccepted())
            .andReturn();

        String jobId = objectMapper.readTree(createResult.getResponse().getContentAsString()).get("job_id").asText();

        mockMvc.perform(get("/v1/admin/audit-logs/export-jobs/{job_id}/download", jobId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "92000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.error_code").value("AUDIT_EXPORT_JOB_NOT_READY"));
    }

    @Test
    void shouldRejectInvalidRange() throws Exception {
        String accessToken = login("ops1", "ops1-pass", "93000000-0000-4000-8000-000000000001").get("access_token").asText();

        mockMvc.perform(post("/v1/admin/audit-logs/export-jobs")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "93000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "format":"json",
                      "from_utc":"2026-03-02T00:00:00Z",
                      "to_utc":"2026-03-01T00:00:00Z"
                    }
                    """))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.error_code").value("AUDIT_EXPORT_RANGE_EXCEEDED"));
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
        JsonNode node = objectMapper.readTree(result.getResponse().getContentAsString());
        assertThat(node.get("access_token").asText()).isNotBlank();
        return node;
    }
}
