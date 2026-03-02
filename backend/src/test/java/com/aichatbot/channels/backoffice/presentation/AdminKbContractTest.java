package com.aichatbot.channels.backoffice.presentation;

import com.aichatbot.contexts.knowledge.rag.application.KbIndexPipelineService;
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
class AdminKbContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private KbIndexPipelineService kbIndexPipelineService;

    @Test
    void shouldHandleKbDocumentAdminFlow() throws Exception {
        String accessToken = login("admin1", "admin1-pass", "a1000000-0000-4000-8000-000000000001")
            .get("access_token")
            .asText();

        MvcResult uploadResult = mockMvc.perform(post("/v1/admin/kb/documents")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000002")
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-kb-upload-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "title":"returns policy update",
                      "source_type":"manual",
                      "category":"cs",
                      "effective_date":"2026-03-01",
                      "owner":"ops-team",
                      "raw_content":"return policy detail paragraph one\\n\\nparagraph two"
                    }
                    """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.status").value("pending"))
            .andExpect(jsonPath("$.pipeline_status").value("QUEUED"))
            .andReturn();

        JsonNode uploaded = objectMapper.readTree(uploadResult.getResponse().getContentAsString());
        String documentId = uploaded.get("document_id").asText();
        int versionNo = uploaded.get("version_no").asInt();
        String indexJobId = uploaded.get("index_job_id").asText();

        mockMvc.perform(get("/v1/admin/kb/documents")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000003")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.items").isArray());

        mockMvc.perform(post("/v1/admin/kb/documents/{doc_id}/approve", documentId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.error_code").value("API-003-409"))
            .andExpect(jsonPath("$.details[0]").value("document_version_not_indexed"));

        kbIndexPipelineService.processPendingJobs(20);

        mockMvc.perform(get("/v1/admin/kb/reindex/{job_id}", indexJobId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("DONE"));

        mockMvc.perform(post("/v1/admin/kb/documents/{doc_id}/approve", documentId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000004")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("approved"));

        mockMvc.perform(post("/v1/admin/kb/documents/{doc_id}/versions/{version}/rollback", documentId, versionNo)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000005")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("rolled_back"));

        MvcResult reindexResult = mockMvc.perform(post("/v1/admin/kb/reindex")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000006")
                .header("X-Tenant-Key", "demo-tenant")
                .header("Idempotency-Key", "idem-kb-reindex-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "note":"nightly refresh"
                    }
                    """))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.status").value("PENDING"))
            .andExpect(jsonPath("$.job_type").value("REINDEX_ALL"))
            .andReturn();

        String jobId = objectMapper.readTree(reindexResult.getResponse().getContentAsString()).get("job_id").asText();

        kbIndexPipelineService.processPendingJobs(20);

        mockMvc.perform(get("/v1/admin/kb/reindex/{job_id}", jobId)
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000007")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("DONE"));

        MvcResult indexOpsResult = mockMvc.perform(get("/v1/admin/kb/index-operations")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000008")
                .header("X-Tenant-Key", "demo-tenant"))
            .andExpect(status().isOk())
            .andReturn();

        JsonNode indexOps = objectMapper.readTree(indexOpsResult.getResponse().getContentAsString());
        assertThat(indexOps.get("items").isArray()).isTrue();
    }

    @Test
    void shouldRejectKbAdminForOpsRole() throws Exception {
        String accessToken = login("ops1", "ops1-pass", "a1000000-0000-4000-8000-000000000010")
            .get("access_token")
            .asText();

        mockMvc.perform(post("/v1/admin/kb/documents")
                .header("Authorization", "Bearer " + accessToken)
                .header("X-Trace-Id", "a1000000-0000-4000-8000-000000000011")
                .header("X-Tenant-Key", "demo-tenant")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "title":"ops no permission"
                    }
                    """))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.error_code").value("SEC-002-403"));
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
