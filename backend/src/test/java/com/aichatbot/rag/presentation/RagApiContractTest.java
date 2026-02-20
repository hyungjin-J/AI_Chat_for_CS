package com.aichatbot.rag.presentation;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest(properties = {
    "app.llm.provider=mock",
    "app.answer.evidence-threshold=0.6"
})
@AutoConfigureMockMvc
class RagApiContractTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void shouldReturnSameRetrieveIdForSameIdempotencyKey() throws Exception {
        String body = """
            {
              "query": "refund policy",
              "top_k": 2,
              "filters": {"category":"CS"}
            }
            """;

        MvcResult first = mockMvc.perform(post("/v1/rag/retrieve")
                .header("X-Trace-Id", "11111111-1111-4111-8111-111111111111")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "SYSTEM")
                .header("Idempotency-Key", "idem-rag-retrieve-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isCreated())
            .andReturn();

        MvcResult second = mockMvc.perform(post("/v1/rag/retrieve")
                .header("X-Trace-Id", "22222222-2222-4222-8222-222222222222")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "SYSTEM")
                .header("Idempotency-Key", "idem-rag-retrieve-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
            .andExpect(status().isCreated())
            .andReturn();

        JsonNode firstJson = objectMapper.readTree(first.getResponse().getContentAsString());
        JsonNode secondJson = objectMapper.readTree(second.getResponse().getContentAsString());
        org.assertj.core.api.Assertions.assertThat(firstJson.get("id").asText()).isEqualTo(secondJson.get("id").asText());
    }

    @Test
    void shouldReturnSafeResponseWhenEvidenceBelowThreshold() throws Exception {
        mockMvc.perform(post("/v1/rag/answer")
                .header("X-Trace-Id", "33333333-3333-4333-8333-333333333333")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "SYSTEM")
                .header("Idempotency-Key", "idem-rag-answer-safe")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "query":"unrelated term for no evidence",
                      "top_k":2,
                      "answer_contract":{"schema_version":"v1","citation_required":true,"fail_closed":true}
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.response_type").value("safe"));
    }

    @Test
    void shouldListCitationsWithPagination() throws Exception {
        MvcResult retrieve = mockMvc.perform(post("/v1/rag/retrieve")
                .header("X-Trace-Id", "44444444-4444-4444-8444-444444444444")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "SYSTEM")
                .header("Idempotency-Key", "idem-rag-retrieve-citation")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "query":"refund",
                      "top_k":2
                    }
                    """))
            .andExpect(status().isCreated())
            .andReturn();
        String retrieveId = objectMapper.readTree(retrieve.getResponse().getContentAsString()).get("id").asText();

        mockMvc.perform(get("/v1/rag/answers/{answer_id}/citations", retrieveId)
                .queryParam("limit", "1")
                .header("X-Trace-Id", "55555555-5555-4555-8555-555555555555")
                .header("X-Tenant-Key", "demo-tenant")
                .header("X-User-Role", "AGENT"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.result").value("ok"))
            .andExpect(jsonPath("$.data.length()").value(1));
    }
}
