package com.aichatbot.billing.presentation;

import com.aichatbot.billing.domain.model.BreachAction;
import com.aichatbot.billing.domain.model.TenantQuota;
import com.aichatbot.billing.infrastructure.GenerationLogRepository;
import com.aichatbot.billing.infrastructure.TenantQuotaRepository;
import java.math.BigDecimal;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "spring.task.scheduling.enabled=false")
@AutoConfigureMockMvc
class BudgetEnforcementHttpTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private TenantQuotaRepository tenantQuotaRepository;

    @Autowired
    private GenerationLogRepository generationLogRepository;

    @BeforeEach
    void setUp() {
        tenantQuotaRepository.clear();
        generationLogRepository.clear();

        tenantQuotaRepository.upsert(new TenantQuota(
            "tenant-budget",
            10,
            1,
            new BigDecimal("9999.0"),
            Instant.parse("2026-01-01T00:00:00Z"),
            null,
            BreachAction.THROTTLE_429,
            "admin",
            "trace-seed",
            Instant.parse("2026-01-01T00:00:00Z")
        ));
    }

    @Test
    void shouldReturn429WithStandardHeadersWhenTokenBudgetExceeded() throws Exception {
        mockMvc.perform(get("/api/v1/sessions/s1/messages/stream")
                .param("prompt", "이 프롬프트는 길어서 토큰 예산을 초과하도록 만든 테스트 입력입니다.")
                .header("X-Trace-Id", "trace-budget")
                .header("X-Tenant-Key", "tenant-budget"))
            .andExpect(status().isTooManyRequests())
            .andExpect(jsonPath("$.error_code").value("API-008-429-BUDGET"))
            .andExpect(jsonPath("$.trace_id").value("trace-budget"))
            .andExpect(header().exists("Retry-After"))
            .andExpect(header().exists("X-RateLimit-Limit"))
            .andExpect(header().exists("X-RateLimit-Remaining"))
            .andExpect(header().exists("X-RateLimit-Reset"));
    }
}

